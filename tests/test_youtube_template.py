import json
from pathlib import Path


TEMPLATE_PATH = Path("docs/n8n/youtube-template.json")


def load_template():
    return json.loads(TEMPLATE_PATH.read_text(encoding="utf-8"))


def test_youtube_template_includes_both_entry_points():
    template = load_template()
    names = {node["name"] for node in template["nodes"]}

    assert "Scheduled Daily Trigger" in names
    assert "Telegram Callback Trigger" in names


def test_youtube_template_includes_approved_production_branch():
    template = load_template()
    names = {node["name"] for node in template["nodes"]}

    required_nodes = {
        "Approval Is Approve?",
        "Build Production Input",
        "Gemini Scenario Planner",
        "Typecast Narration",
        "Upload Narration to S3",
        "Gemini Still Image",
        "Veo Lite Hook Clip",
        "Start Render Job",
        "YouTube Upload",
    }

    assert required_nodes.issubset(names)


def test_youtube_template_has_wired_connections():
    template = load_template()

    assert template["connections"]
    assert "Scheduled Daily Trigger" in template["connections"]
    assert "Telegram Callback Trigger" in template["connections"]
    assert "Approval Is Approve?" in template["connections"]


def test_youtube_template_uses_supported_veo_duration():
    template = load_template()
    veo_node = next(node for node in template["nodes"] if node["name"] == "Veo Lite Hook Clip")

    assert veo_node["parameters"]["modelId"]["value"] == "={{$('Expand Scenes').item.json.veo_model}}"
    assert veo_node["parameters"]["prompt"] == "={{$('Expand Scenes').item.json.scene_video_prompt}}"
    assert veo_node["parameters"]["options"]["durationSeconds"] == "={{$('Expand Scenes').item.json.scene_video_duration_seconds}}"
    assert "personGeneration" not in veo_node["parameters"]["options"]


def test_build_production_input_supports_style_profiles():
    template = load_template()
    node = next(node for node in template["nodes"] if node["name"] == "Build Production Input")
    js_code = node["parameters"]["jsCode"]

    assert "const styleProfiles = {" in js_code
    assert "const styleProfile = $json.style_profile || 'mystery';" in js_code
    assert "style_profile: styleProfile" in js_code
    assert "style: selected.style" in js_code
    assert "visual_style: selected.visual_style" in js_code
    assert "veo_model: 'models/veo-3.1-lite-generate-preview'" in js_code


def test_gemini_still_image_uses_first_still_image_prompt():
    template = load_template()
    node = next(node for node in template["nodes"] if node["name"] == "Gemini Still Image")

    assert node["parameters"]["prompt"] == "={{$json.still_image_prompt}}"


def test_scene_generation_uses_loop_and_retry_nodes():
    template = load_template()
    names = {node["name"] for node in template["nodes"]}

    required_nodes = {
        "Loop Over Scenes",
        "Wait Before Image Retry",
        "Wait Before Veo",
        "Check Video Output",
        "Video OK?",
        "Wait Before Veo Retry",
        "Veo Lite Hook Clip Retry",
        "Check Video Output Retry",
        "Retry Video OK?",
        "Fail Video Scene",
    }

    assert required_nodes.issubset(names)


def test_scene_generation_wiring_is_sequential():
    template = load_template()
    connections = template["connections"]
    loop_node = next(node for node in template["nodes"] if node["name"] == "Loop Over Scenes")

    assert loop_node["parameters"]["batchSize"] == 1
    assert connections["Expand Scenes"]["main"][0][0]["node"] == "Loop Over Scenes"
    assert connections["Loop Over Scenes"]["main"][0][0]["node"] == "Prepare Render Manifest"
    assert connections["Loop Over Scenes"]["main"][1][0]["node"] == "Gemini Still Image"
    assert connections["Upload Hook Video to S3"]["main"][0][0]["node"] == "Loop Over Scenes"


def test_gemini_scenario_planner_has_larger_output_budget():
    template = load_template()
    node = next(node for node in template["nodes"] if node["name"] == "Gemini Scenario Planner")

    assert node["parameters"]["options"]["maxOutputTokens"] >= 8192


def test_start_render_job_uses_stringified_json_body():
    template = load_template()
    node = next(node for node in template["nodes"] if node["name"] == "Start Render Job")

    assert "JSON.stringify" in node["parameters"]["jsonBody"]


def test_persist_telegram_message_id_maps_style_profile():
    template = load_template()
    node = next(node for node in template["nodes"] if node["name"] == "Persist Telegram Message Id")
    values = node["parameters"]["columns"]["value"]

    assert values["style_profile"] == "={{$('Format Telegram Approval').item.json.style_profile}}"
