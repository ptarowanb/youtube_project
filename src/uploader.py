from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo


YOUTUBE_UPLOAD_SCOPE = ["https://www.googleapis.com/auth/youtube.upload"]
KST = ZoneInfo("Asia/Seoul")


def parse_publish_at(value: str) -> datetime:
    local_dt = datetime.strptime(value, "%Y-%m-%d %H:%M")
    return local_dt.replace(tzinfo=KST).astimezone(timezone.utc)


def build_upload_request_body(
    metadata: dict,
    schedule_time: datetime | None = None,
) -> dict:
    visibility = metadata.get("visibility", "private")
    status: dict[str, str] = {"privacyStatus": visibility}

    if schedule_time is not None:
        status["privacyStatus"] = "private"
        status["publishAt"] = schedule_time.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    return {
        "snippet": {
            "title": metadata.get("title", ""),
            "description": metadata.get("description", ""),
            "tags": metadata.get("tags", []),
        },
        "status": status,
    }


def _resolve_client_secret_path(channel_config: dict) -> Path:
    configured = channel_config.get("youtube_client_secret_path", "configs/client_secret.json")
    return Path(configured)


def _resolve_token_path(channel_config: dict) -> Path:
    configured = channel_config.get("youtube_token_path", "configs/token.json")
    return Path(configured)


def load_youtube_credentials(channel_config: dict):
    client_secret_path = _resolve_client_secret_path(channel_config)
    token_path = _resolve_token_path(channel_config)

    if not client_secret_path.exists():
        raise FileNotFoundError(f"Missing YouTube client secret file: {client_secret_path}")

    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow

    credentials = None
    if token_path.exists():
        credentials = Credentials.from_authorized_user_file(str(token_path), YOUTUBE_UPLOAD_SCOPE)

    if credentials and credentials.valid:
        return credentials

    if credentials and credentials.expired and credentials.refresh_token:
        credentials.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file(str(client_secret_path), YOUTUBE_UPLOAD_SCOPE)
        credentials = flow.run_local_server(port=0)

    token_path.parent.mkdir(parents=True, exist_ok=True)
    token_path.write_text(credentials.to_json(), encoding="utf-8")
    return credentials


def build_youtube_service(channel_config: dict):
    credentials = load_youtube_credentials(channel_config)
    from googleapiclient.discovery import build

    return build("youtube", "v3", credentials=credentials)


def upload_video(
    video_path: Path,
    metadata: dict,
    channel_config: dict,
    schedule_time: datetime | None = None,
) -> str:
    if not Path(video_path).exists():
        raise FileNotFoundError(f"Video file does not exist: {video_path}")

    body = build_upload_request_body(metadata, schedule_time=schedule_time)
    service = build_youtube_service(channel_config)

    from googleapiclient.http import MediaFileUpload

    media = MediaFileUpload(str(video_path), resumable=True)
    request = service.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )
    response = request.execute()
    return response["id"]
