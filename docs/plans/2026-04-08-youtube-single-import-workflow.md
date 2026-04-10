# YouTube Single Import Workflow Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build one importable `n8n` workflow JSON that combines channel harvesting, Gemini analysis, Telegram approval, and approved-only Shorts production into a single template.

**Architecture:** Keep the logic in one `youtube-template.json` workflow with two triggers. The scheduled branch handles harvesting and idea generation; the Telegram callback branch handles approval status changes and only launches the existing production path when an idea is approved.

**Tech Stack:** n8n workflow JSON, Google Sheets node, YouTube node, Google Gemini node, Telegram node/trigger, Typecast HTTP API, AWS S3 node, HTTP Request node, Wait node, YouTube upload node

---

### Task 1: Document the single-workflow architecture

**Files:**
- Create: `docs/plans/2026-04-08-youtube-single-import-workflow-design.md`
- Modify: `docs/n8n/youtube-template.md`

**Step 1: Write the design summary**

Document:
- why the workflow is being merged into one importable JSON
- the two trigger entry points
- where production costs start

**Step 2: Write the Sheets schema**

Document exact columns for:
- `channels`
- `source_videos`
- `ideas`

**Step 3: Verify docs render**

Run:

```powershell
Get-Content docs/plans/2026-04-08-youtube-single-import-workflow-design.md
Get-Content docs/n8n/youtube-template.md
```

Expected: both files describe the single import workflow and Sheets schema.

### Task 2: Rewrite `youtube-template.json` as one importable workflow

**Files:**
- Modify: `docs/n8n/youtube-template.json`
- Modify: `docs/n8n/youtube-template.md`

**Step 1: Add the scheduled harvest branch**

Include nodes for:
- `Schedule Trigger`
- `Compute Lookback`
- `Read Channels in Sheets`
- `Filter Enabled Channels`
- `Fetch Channel Videos`
- `Normalize Harvested Videos`
- dedupe against `source_videos`
- append only new rows

**Step 2: Add Gemini analysis and draft idea creation**

Add nodes for:
- reading new `source_videos`
- `Gemini` analysis prompt
- parsing JSON output into `ideas`
- appending `draft` rows into the `ideas` tab

**Step 3: Add Telegram approval request nodes**

Add nodes for:
- formatting the approval summary
- sending Telegram messages with inline buttons
- persisting `telegram_message_id`

**Step 4: Add Telegram callback branch**

Add nodes for:
- `Telegram Trigger`
- parsing callback data
- loading the matching `ideas` row
- updating `status`, `review_action`, and `approved_at`

**Step 5: Add approved-only production branch**

Add nodes for:
- `Gemini` script/meta generation
- `Typecast` narration
- `Gemini Image`
- `Veo Lite`
- `AWS S3` uploads
- `/render-jobs` request
- polling
- YouTube upload

**Step 6: Validate JSON syntax**

Run:

```powershell
python -m json.tool docs/n8n/youtube-template.json > $null
```

Expected: command exits successfully.

### Task 3: Update template documentation for operator setup

**Files:**
- Modify: `docs/n8n/youtube-template.md`

**Step 1: Document required credentials**

List:
- `googleSheetsOAuth2Api` or service account
- `youTubeOAuth2Api`
- `googlePalmApi`
- `telegramApi`
- `aws`

**Step 2: Document required env vars**

List:
- `TYPECAST_API_KEY`
- `AUTOMATION_SHARED_TOKEN`
- `RENDER_BUCKET_NAME`

**Step 3: Document the setup sequence**

Document:
- fill Google Sheets
- import workflow
- attach credentials
- set env vars
- activate workflow

**Step 4: Verify docs render**

Run:

```powershell
Get-Content docs/n8n/youtube-template.md
```

Expected: file documents credentials, env vars, and sheet schema.

### Task 4: Verify the combined template

**Files:**
- Modify: `docs/n8n/youtube-template.json`
- Modify: `docs/n8n/youtube-template.md`

**Step 1: Run JSON validation**

Run:

```powershell
python -m json.tool docs/n8n/youtube-template.json > $null
```

Expected: success.

**Step 2: Sanity-check structure**

Run:

```powershell
Get-Content docs/n8n/youtube-template.json | Select-Object -First 80
Get-Content docs/n8n/youtube-template.md | Select-Object -First 120
```

Expected:
- JSON shows both triggers
- markdown explains the combined workflow

**Step 3: Commit**

```bash
git add docs/n8n/youtube-template.json docs/n8n/youtube-template.md docs/plans/2026-04-08-youtube-single-import-workflow-design.md docs/plans/2026-04-08-youtube-single-import-workflow.md
git commit -m "docs: merge youtube workflow into single import template"
```

Plan complete and saved to `docs/plans/2026-04-08-youtube-single-import-workflow.md`. Two execution options:

**1. Subagent-Driven (this session)** - I dispatch fresh subagent per task, review between tasks, fast iteration

**2. Parallel Session (separate)** - Open new session with executing-plans, batch execution with checkpoints

**Which approach?**
