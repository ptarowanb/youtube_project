# YouTube Research To Telegram Approval Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a documented n8n workflow architecture that harvests competitor channel videos into Google Sheets, analyzes them with Gemini, sends draft ideas to Telegram for approval, and only then triggers the existing Shorts generation pipeline.

**Architecture:** Keep research, review, and production as separate workflows. Use Google Sheets as the operator-facing control plane, Telegram inline buttons as the approval gate, and the existing `end-to-end-ai-render-youtube-template` as the downstream production workflow for `approved` ideas only.

**Tech Stack:** n8n workflow JSON, Google Sheets node, YouTube node, Google Gemini node, Telegram node/trigger, Wait node, HTTP Request node, AWS S3 node

---

### Task 1: Document the approved architecture

**Files:**
- Create: `docs/plans/2026-04-08-youtube-research-telegram-approval-design.md`
- Modify: `docs/n8n/end-to-end-ai-render-youtube-template.md`

**Step 1: Write the design summary**

Document:
- `channels -> source_videos -> ideas -> Telegram approval -> approved production`
- why we are not reusing competitor video files directly
- where costs are incurred

**Step 2: Write the Sheets schema**

Document exact columns for:
- `channels`
- `source_videos`
- `ideas`

**Step 3: Verify docs render**

Run:

```powershell
Get-Content docs/plans/2026-04-08-youtube-research-telegram-approval-design.md
Get-Content docs/n8n/end-to-end-ai-render-youtube-template.md
```

Expected: both files show the Telegram approval and Sheets schema sections.

### Task 2: Refactor the research workflow template

**Files:**
- Modify: `docs/n8n/youtube-template.json`
- Create: `docs/n8n/youtube-research-telegram-approval-template.md`

**Step 1: Replace hardcoded channels with Sheets-driven channel loading**

Remove the fixed `Fetch ... Videos` fan-out pattern and replace it with:
- `Read Channels in Sheets`
- filter `enabled=TRUE`
- iterate over channel rows
- fetch videos for each channel

**Step 2: Replace hardcoded dates with dynamic lookback**

Use one node to compute:

```javascript
const days = 3;
const since = new Date(Date.now() - days * 24 * 60 * 60 * 1000).toISOString();
return [{ json: { published_after: since } }];
```

Then wire `publishedAfter` to that field.

**Step 3: Normalize harvested videos**

Add a `Code` node that emits:

```javascript
return items.map(item => ({
  json: {
    video_id: item.json.id,
    channel_id: item.json.snippet?.channelId,
    channel_name: item.json.snippet?.channelTitle,
    title: item.json.snippet?.title,
    url: `https://www.youtube.com/watch?v=${item.json.id}`,
    published_at: item.json.snippet?.publishedAt,
    harvested_at: new Date().toISOString(),
    status: 'new',
  }
}));
```

**Step 4: Deduplicate against `source_videos`**

Read existing sheet rows, compare by `video_id`, and only append unseen items.

**Step 5: Validate JSON syntax**

Run:

```powershell
python -m json.tool docs/n8n/youtube-template.json > $null
```

Expected: command exits successfully.

### Task 3: Add Gemini analysis and idea creation workflow

**Files:**
- Modify: `docs/n8n/youtube-template.json`
- Create: `docs/n8n/youtube-research-telegram-approval-template.md`

**Step 1: Add a Gemini analysis block**

Use a `Google Gemini` text node that receives:
- channel name
- video title
- video URL

Prompt it to return JSON with:
- `topic`
- `hook`
- `angle`
- `summary`
- `suggested_title`
- `suggested_description`
- `suggested_tags`

**Step 2: Parse Gemini output**

Add a `Code` node that parses the JSON and creates:

```javascript
return [{
  json: {
    idea_id: `idea_${Date.now()}`,
    source_video_id: $json.video_id,
    channel_name: $json.channel_name,
    topic: parsed.topic,
    hook: parsed.hook,
    angle: parsed.angle,
    summary: parsed.summary,
    suggested_title: parsed.suggested_title,
    suggested_description: parsed.suggested_description,
    suggested_tags: parsed.suggested_tags,
    status: 'draft'
  }
}];
```

**Step 3: Append to `ideas` sheet**

Map the parsed fields into the `ideas` tab.

**Step 4: Verify output contract**

Check that `ideas` rows contain:
- `idea_id`
- `source_video_id`
- `status=draft`

### Task 4: Add Telegram review workflow

**Files:**
- Modify: `docs/n8n/youtube-template.json`
- Create: `docs/n8n/youtube-research-telegram-approval-template.md`

**Step 1: Add a draft idea reader**

Read `ideas` where `status=draft` and `telegram_message_id` is empty.

**Step 2: Add a Telegram send node**

Send a formatted summary message containing:
- channel name
- source video URL
- topic
- hook
- angle
- summary

**Step 3: Add inline keyboard metadata**

Encode callback data as:

```text
approve|<idea_id>
hold|<idea_id>
reject|<idea_id>
```

**Step 4: Persist `telegram_message_id`**

Update the corresponding `ideas` row after sending.

### Task 5: Add Telegram callback approval workflow

**Files:**
- Modify: `docs/n8n/youtube-template.json`
- Create: `docs/n8n/youtube-research-telegram-approval-template.md`

**Step 1: Add `Telegram Trigger` for callback queries**

Listen for callback events only.

**Step 2: Parse callback data**

Use a `Code` node:

```javascript
const [action, ideaId] = $json.callback_query.data.split('|');
return [{ json: { action, idea_id: ideaId } }];
```

**Step 3: Update the `ideas` row**

Map:
- `approve -> approved`
- `hold -> hold`
- `reject -> rejected`

Also write:
- `review_action`
- `approved_at` when action is approve

**Step 4: Edit the Telegram message**

Update the original message text or append status so the operator sees the decision was applied.

### Task 6: Wire approved ideas into the production workflow

**Files:**
- Modify: `docs/n8n/end-to-end-ai-render-youtube-template.json`
- Modify: `docs/n8n/end-to-end-ai-render-youtube-template.md`

**Step 1: Define approved-idea input contract**

Document the input shape:

```json
{
  "idea_id": "idea_123",
  "topic": "topic",
  "hook": "hook",
  "angle": "angle",
  "suggested_title": "title",
  "suggested_description": "desc",
  "suggested_tags": ["tag1", "tag2"]
}
```

**Step 2: Add a pre-production normalization step**

Map approved idea fields into the current generation workflow input.

**Step 3: Ensure the generation workflow can be triggered by approval**

Decide whether:
- `approved` rows are polled by schedule
- or callback workflow directly calls the production webhook

Implement only one. Prefer direct webhook call for simplicity.

**Step 4: Verify production template still parses**

Run:

```powershell
python -m json.tool docs/n8n/end-to-end-ai-render-youtube-template.json > $null
```

Expected: command exits successfully.

### Task 7: Final verification

**Files:**
- Review: `docs/n8n/youtube-template.json`
- Review: `docs/n8n/end-to-end-ai-render-youtube-template.json`
- Review: `docs/plans/2026-04-08-youtube-research-telegram-approval-design.md`
- Review: `docs/plans/2026-04-08-youtube-research-telegram-approval.md`

**Step 1: Verify both JSON files parse**

Run:

```powershell
python -m json.tool docs/n8n/youtube-template.json > $null
python -m json.tool docs/n8n/end-to-end-ai-render-youtube-template.json > $null
```

Expected: both commands exit successfully.

**Step 2: Verify the design matches the JSON**

Check that the docs mention:
- Sheets-driven channel list
- Telegram inline approval
- approved-only production

**Step 3: Commit**

```bash
git add docs/n8n/youtube-template.json docs/n8n/end-to-end-ai-render-youtube-template.json docs/n8n/youtube-research-telegram-approval-template.md docs/plans/2026-04-08-youtube-research-telegram-approval-design.md docs/plans/2026-04-08-youtube-research-telegram-approval.md
git commit -m "docs: add YouTube research and Telegram approval workflow plan"
```
