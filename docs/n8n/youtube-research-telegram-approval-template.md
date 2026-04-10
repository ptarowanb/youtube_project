# YouTube Research Workflow Template

This template is the research-only YouTube ingestion workflow.

Scope:

- Load enabled channels from Google Sheets
- Compute a dynamic 3-day lookback window
- Fetch videos per channel
- Normalize harvested video rows
- Deduplicate against `source_videos`
- Append only unseen rows back to Sheets

Out of scope for this template:

- Gemini analysis
- Telegram approval
- Production triggering
- Upload or publish steps

Expected Sheets:

- `channels`
- `source_videos`

The workflow is intentionally importable without live credentials or hardcoded channel lists.
