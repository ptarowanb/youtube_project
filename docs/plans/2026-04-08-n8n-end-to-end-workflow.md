# N8N End-To-End Workflow Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Create an importable n8n workflow JSON that covers Gemini-driven planning, Typecast narration, Gemini Image and Veo Lite generation, S3 uploads, render job submission, render polling, and YouTube upload.

**Architecture:** Use a single webhook-driven orchestration workflow. Implement the balanced provider path with actual `Google Gemini`, `HTTP Request`, and `AWS S3` nodes, while keeping the scene count intentionally small in this template. The render manifest includes `video_keys` for Veo Lite hook clips.

**Tech Stack:** n8n workflow JSON, Webhook node, Code node, Google Gemini node, HTTP Request node, AWS S3 node, Wait node, If node, YouTube node, Gemini API, Typecast API, Veo Lite

---

### Task 1: Add design and operator docs

**Files:**
- Create: `docs/plans/2026-04-08-n8n-end-to-end-workflow-design.md`
- Create: `docs/n8n/end-to-end-ai-render-youtube-template.md`

**Step 1: Write the design summary**

Document the overall flow:
- Gemini planning in n8n
- Typecast narration in n8n
- Gemini Image + Veo Lite generation in n8n
- S3 uploads for every generated artifact
- S3 manifest preparation
- `/render-jobs` call
- render polling
- YouTube upload

**Step 2: Document the runtime contract**

Document:
- webhook input example
- `/render-jobs` request example
- render status response example

**Step 3: Verify docs exist**

Run:

```powershell
Get-Content docs/plans/2026-04-08-n8n-end-to-end-workflow-design.md
Get-Content docs/n8n/end-to-end-ai-render-youtube-template.md
```

Expected: both files render without missing sections.

### Task 2: Add the end-to-end workflow JSON template

**Files:**
- Create: `docs/n8n/end-to-end-ai-render-youtube-template.json`

**Step 1: Define the node sequence**

Include nodes for:
- webhook trigger
- normalize input
- Gemini scenario generation
- Typecast narration generation
- S3 upload for narration and subtitles
- Gemini image generation
- Veo Lite video generation
- S3 upload for visual assets
- render submit
- webhook response
- wait/poll
- YouTube upload

**Step 2: Keep provider-specific steps replaceable**

Use clearly named provider blocks and sticky notes so users can later extend:
- Gemini/script generation
- Typecast TTS
- Gemini Image generation
- Veo Lite generation
- S3 upload nodes

**Step 3: Make render/publish steps concrete**

Use actual expressions for:
- `POST /render-jobs`
- `GET /render-jobs/{id}`
- `video_url` / `output_url`
- YouTube upload metadata

**Step 4: Validate JSON syntax**

Run:

```powershell
python -m json.tool docs/n8n/end-to-end-ai-render-youtube-template.json > $null
```

Expected: command exits successfully with no JSON parse error.

### Task 3: Final verification

**Files:**
- Review: `docs/n8n/end-to-end-ai-render-youtube-template.json`
- Review: `docs/n8n/end-to-end-ai-render-youtube-template.md`

**Step 1: Sanity-check node assumptions**

Verify the template assumes:
- `AUTOMATION_SHARED_TOKEN` is available to n8n runtime
- automation returns `done` plus `video_url` or `output_url`
- YouTube credential must be attached manually
- balanced mode uses a small number of Veo Lite clips rather than full-video generation

**Step 2: Summarize what must be replaced**

List the sections that most likely need channel-specific extension:
- additional still image loops
- additional Veo Lite hook loops
- richer subtitle segmentation
- thumbnail-specific generation

**Step 3: Commit**

```bash
git add docs/plans/2026-04-08-n8n-end-to-end-workflow-design.md docs/plans/2026-04-08-n8n-end-to-end-workflow.md docs/n8n/end-to-end-ai-render-youtube-template.json docs/n8n/end-to-end-ai-render-youtube-template.md
git commit -m "docs: add end-to-end n8n workflow template"
```
