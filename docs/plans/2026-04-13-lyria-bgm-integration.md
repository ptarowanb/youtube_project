# Lyria BGM Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add style-aware 30-second background music generation with Lyria to the n8n workflow and pass the generated track into the automation renderer for final mixing under narration.

**Architecture:** Keep Veo responsible for video only. Generate one 30-second instrumental WAV track with Lyria after scenario planning, upload it to S3, attach the S3 key to the render manifest, and let `automation` mix the generated BGM with narration at a low level. Preserve a no-BGM fallback so render jobs do not fail if music generation fails.

**Tech Stack:** n8n Code nodes, n8n HTTP Request node, Vertex AI Lyria 2 REST API, AWS S3, Python automation service, ffmpeg, pytest

---

### Task 1: Remove the hardcoded fallback BGM key

**Files:**
- Modify: `docs/n8n/youtube-template.json`
- Test: `tests/test_youtube_template.py`

**Step 1: Write the failing test**

Add an assertion that `Build Production Input` no longer hardcodes `shared/bgm/default.mp3`.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_youtube_template.py -q`
Expected: FAIL because `bgm_key` is still hardcoded.

**Step 3: Write minimal implementation**

In `Build Production Input`, change `bgm_key` to use an empty default:

```javascript
bgm_key: $json.bgm_key || '',
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_youtube_template.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add docs/n8n/youtube-template.json tests/test_youtube_template.py
git commit -m "refactor: remove hardcoded fallback bgm key"
```

### Task 2: Add a style-aware BGM prompt builder node

**Files:**
- Modify: `docs/n8n/youtube-template.json`

**Step 1: Add a new `Code` node after `Parse Scenario`**

Node name: `Build BGM Prompt`

The node should output the original scenario fields plus:
- `bgm_prompt`
- `bgm_negative_prompt`

Recommended code:

```javascript
const styleProfile = $json.style_profile || 'mystery';

const prompts = {
  mystery: 'Minimal dark ambient instrumental background music for Korean Shorts narration. No vocals. No lead melody. No dramatic hits. Low energy. Sparse texture. Leave space for voice. 30 seconds.',
  emotional: 'Minimal warm emotional instrumental background music for Korean Shorts narration. Soft piano pad. No vocals. No lead melody. Very subtle. Low energy. Leave space for voice. 30 seconds.',
  news: 'Minimal clean factual instrumental background music for Korean Shorts narration. Soft neutral pulse. No vocals. No dramatic hits. No big transitions. Very subtle. Leave space for voice. 30 seconds.',
  knowledge: 'Minimal smart educational instrumental background music for Korean Shorts narration. Clean soft marimba and pad. No vocals. No lead melody. Low energy. Leave space for voice. 30 seconds.',
};

return [{
  json: {
    ...$json,
    bgm_prompt: prompts[styleProfile] || prompts.mystery,
    bgm_negative_prompt: 'vocals, singing, choir, rap, strong lead melody, aggressive drums, cinematic boom, riser, drop, loud percussion, abrupt transitions'
  }
}];
```

**Step 2: Wire the node**

Reconnect the flow so `Parse Scenario -> Build BGM Prompt`.

**Step 3: Commit**

```bash
git add docs/n8n/youtube-template.json
git commit -m "feat: add lyria bgm prompt builder node"
```

### Task 3: Add the Lyria generation node

**Files:**
- Modify: `docs/n8n/youtube-template.json`
- Check: Google Cloud Lyria docs

**Step 1: Add a new `HTTP Request` node after `Build BGM Prompt`**

Node name: `Generate BGM`

Use the Vertex AI REST endpoint:

```text
https://us-central1-aiplatform.googleapis.com/v1/projects/{{$env.GCP_PROJECT_ID}}/locations/us-central1/publishers/google/models/lyria-002:predict
```

This is based on the official Lyria 2 docs. Lyria returns base64 WAV audio and is intended for instrumental music. Prompts should be in US English.

**Step 2: Configure request**

- Method: `POST`
- Send Headers: `true`
- Header `Content-Type`: `application/json`
- Header `Authorization`: `Bearer <Vertex AI access token>`
- Response format: `json`
- Enable `Continue On Fail`

Request body:

```json
{
  "instances": [
    {
      "prompt": "={{$json.bgm_prompt}}",
      "negative_prompt": "={{$json.bgm_negative_prompt}}"
    }
  ],
  "parameters": {
    "sample_count": 1
  }
}
```

**Step 3: Add environment/config prerequisites**

The workflow now needs:
- `GCP_PROJECT_ID`
- a way for n8n to send a valid Vertex AI bearer token

Do not guess the token flow in the plan. Choose one concrete auth path before implementation:
- service account backed HTTP auth in n8n
- a small internal token minting service
- a pre-provisioned short-lived token injection step

**Step 4: Commit**

```bash
git add docs/n8n/youtube-template.json
git commit -m "feat: add lyria bgm generation node"
```

### Task 4: Decode the generated WAV into binary

**Files:**
- Modify: `docs/n8n/youtube-template.json`

**Step 1: Add a `Code` node after `Generate BGM`**

Node name: `Decode BGM Audio`

Responsibilities:
- keep the full scenario payload
- if `predictions[0].audioContent` exists, decode it into binary property `data`
- if not, keep `bgm_key` empty and do not throw

Suggested logic:

```javascript
const source = $('Build BGM Prompt').first().json;
const prediction = $json.predictions?.[0];

if (!prediction?.audioContent) {
  return [{
    json: {
      ...source,
      bgm_key: ''
    }
  }];
}

const data = Buffer.from(prediction.audioContent, 'base64');

return [{
  json: {
    ...source
  },
  binary: {
    data: await this.helpers.prepareBinaryData(
      data,
      'bed.wav',
      prediction.mimeType || 'audio/wav'
    )
  }
}];
```

**Step 2: Commit**

```bash
git add docs/n8n/youtube-template.json
git commit -m "feat: decode lyria bgm audio response"
```

### Task 5: Upload the generated BGM to S3

**Files:**
- Modify: `docs/n8n/youtube-template.json`

**Step 1: Add an `AWS S3` upload node**

Node name: `Upload BGM to S3`

Settings:
- Resource: `file`
- Operation: `upload`
- Bucket: `={{$json.render_bucket_name}}`
- Input Data Field Name: `data`
- File Name: `bed.wav`
- Parent Folder:

```text
={{'jobs/' + $json.job_id + '/bgm'}}
```

**Step 2: Add a `Set` or `Code` node after upload**

Node name: `Attach BGM Key`

Set:

```javascript
bgm_key: 'jobs/' + $json.job_id + '/bgm/bed.wav'
```

The node should preserve the rest of the scenario payload.

**Step 3: Commit**

```bash
git add docs/n8n/youtube-template.json
git commit -m "feat: upload generated bgm and attach s3 key"
```

### Task 6: Add a clean no-BGM fallback branch

**Files:**
- Modify: `docs/n8n/youtube-template.json`

**Step 1: Add an `If` node after `Decode BGM Audio`**

Node name: `Has BGM Binary?`

Condition:
- check whether binary property `data` exists

**Step 2: False branch**

Add `Set Empty BGM Key`

It should emit the full scenario item with:

```javascript
bgm_key: ''
```

**Step 3: True branch**

Send to `Upload BGM to S3 -> Attach BGM Key`

**Step 4: Merge the branches**

Add a merge node, e.g. `Merge BGM Result`, and feed its output into `Prepare Render Manifest`.

This keeps render jobs alive when music generation fails or Vertex AI is unavailable.

**Step 5: Commit**

```bash
git add docs/n8n/youtube-template.json
git commit -m "feat: add no-bgm fallback branch"
```

### Task 7: Rewire the render manifest path

**Files:**
- Modify: `docs/n8n/youtube-template.json`

**Step 1: Update `Prepare Render Manifest` input source**

Make sure `Prepare Render Manifest` receives the scenario payload after BGM processing, not directly from `Parse Scenario`.

The output contract must include:
- `job_id`
- `video_keys`
- `image_keys`
- `audio_keys`
- `subtitle_key`
- `bgm_key`
- `output_prefix`

**Step 2: Keep `Start Render Job` payload unchanged**

The existing request body is already correct as long as `bgm_key` is now either a real S3 key or an empty string.

**Step 3: Commit**

```bash
git add docs/n8n/youtube-template.json
git commit -m "refactor: feed render manifest from bgm pipeline"
```

### Task 8: Make automation treat BGM as optional

**Files:**
- Modify: `src/automation_server.py`
- Test: `tests/test_automation_server.py`

**Step 1: Write the failing test**

Add a test where `bgm_key` points to a missing object and assert the job still completes without BGM.

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_automation_server.py -q`
Expected: FAIL because the renderer currently dies on missing BGM downloads.

**Step 3: Implement minimal behavior**

Change the optional asset download path so:
- `subtitle_key` missing is allowed
- `bgm_key` missing is allowed
- video/image/audio missing still fails

Also add request/response logs for:
- incoming `POST /render-jobs`
- accepted job id
- `GET /render-jobs/{id}` status lookups
- download failures for optional BGM

**Step 4: Run tests**

Run: `python -m pytest tests/test_automation_server.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add src/automation_server.py tests/test_automation_server.py
git commit -m "feat: make bgm optional in automation renderer"
```

### Task 9: Tune the mix so BGM stays under narration

**Files:**
- Modify: `src/automation_server.py`

**Step 1: Keep BGM gain low**

Current mix should target a quiet bed. Start around:
- narration volume: `1.0`
- bgm volume: `0.10` to `0.15`

**Step 2: Leave room for a later ducking pass**

Do not overbuild sidechain compression in the first pass. Keep the first implementation minimal:
- fixed low BGM volume
- narration dominant

Only add dynamic ducking if the simple mix is clearly insufficient after listening tests.

**Step 3: Commit**

```bash
git add src/automation_server.py
git commit -m "tune: keep bgm subtle under narration"
```

### Task 10: Verify end-to-end behavior

**Files:**
- Check: `docs/n8n/youtube-template.json`
- Check: CloudWatch logs for `/ecs/automation`

**Step 1: Run local tests**

Run: `python -m pytest -q`
Expected: PASS

**Step 2: Manual n8n verification**

Confirm in a single execution:
- `Build BGM Prompt` outputs the expected style prompt
- `Generate BGM` returns `predictions[0].audioContent`
- `Upload BGM to S3` uploads `jobs/<job_id>/bgm/bed.wav`
- `Prepare Render Manifest` includes a real `bgm_key`
- `Start Render Job` sends that key

**Step 3: Runtime verification**

Check CloudWatch `/ecs/automation` logs for:
- request accepted
- job start
- optional BGM missing warnings when relevant
- job done or failed

**Step 4: Audio check**

Listen to the final mp4 and confirm:
- BGM is audible but understated
- narration remains dominant
- no abrupt transitions or loud intros

**Step 5: Commit**

```bash
git add docs/n8n/youtube-template.json src/automation_server.py tests/test_automation_server.py tests/test_youtube_template.py
git commit -m "feat: add lyria bgm generation pipeline"
```
