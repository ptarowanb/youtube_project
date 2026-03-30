# Manual Script Workflow Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a human-friendly Markdown script form, parse it into the pipeline, and optionally upload the rendered video to YouTube from the CLI.

**Architecture:** Keep the existing render pipeline intact and add a new input path through a dedicated parser module. Uploader stays optional behind a CLI flag so local rendering remains usable without OAuth setup.

**Tech Stack:** Python 3.10+, pytest, PyYAML, MoviePy, google-api-python-client, google-auth-oauthlib

---

### Task 1: Document the Markdown script form

**Files:**
- Create: `docs/manual-script-form.md`
- Modify: `README.md`

**Step 1: Write the documentation content**

Document:
- required and optional fields
- copy-paste template
- prompt instructions for generating scripts in this form
- CLI example using `--script-file`

**Step 2: Verify the document is clear**

Run: `Get-Content -Raw docs/manual-script-form.md`
Expected: includes one full example and a blank template.

### Task 2: Add Markdown script parser with TDD

**Files:**
- Create: `src/manual_script_parser.py`
- Create: `tests/test_manual_script_parser.py`

**Step 1: Write the failing test**

Cover:
- parsing complete form into `ScriptPayload`
- mapping `visual_hint` to `image_prompt`
- parsing tags and description
- rejecting missing title/channel/segments

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_manual_script_parser.py -v`
Expected: FAIL because parser module does not exist.

**Step 3: Write minimal implementation**

Implement:
- markdown section parser
- metadata extraction
- segment extraction
- payload normalization

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_manual_script_parser.py -v`
Expected: PASS

### Task 3: Integrate `--script-file` into the CLI with TDD

**Files:**
- Modify: `src/main.py`
- Modify: `tests/test_main.py`

**Step 1: Write the failing test**

Cover:
- parser accepts `--script-file`
- `run_pipeline` can render from a script file without `--topic`
- channel comes from the script metadata by default

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_main.py -v`
Expected: FAIL on missing CLI behavior.

**Step 3: Write minimal implementation**

Implement:
- CLI args
- script-file load path
- metadata precedence rules

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_main.py -v`
Expected: PASS

### Task 4: Implement optional YouTube uploader with TDD

**Files:**
- Modify: `src/uploader.py`
- Create: `tests/test_uploader.py`
- Modify: `requirements.txt`
- Modify: `.env.example`

**Step 1: Write the failing test**

Cover:
- request metadata body generation
- visibility mapping
- `publishAt` inclusion when scheduled
- missing credential file failure path

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_uploader.py -v`
Expected: FAIL because uploader is still a stub.

**Step 3: Write minimal implementation**

Implement:
- request body builder
- OAuth credential loader
- upload entrypoint using `googleapiclient.discovery.build`
- isolated helpers so tests can mock network calls

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_uploader.py -v`
Expected: PASS

### Task 5: Wire `--upload` into the main flow with TDD

**Files:**
- Modify: `src/main.py`
- Modify: `tests/test_main.py`

**Step 1: Write the failing test**

Cover:
- `--upload` calls uploader after render
- `--visibility` and `--publish-at` override script metadata
- default run does not call uploader

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_main.py -v`
Expected: FAIL on upload flow assertions.

**Step 3: Write minimal implementation**

Implement optional uploader call after successful render and return upload result in the run summary.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_main.py -v`
Expected: PASS

### Task 6: Final verification

**Files:**
- Modify as needed based on failures

**Step 1: Run the full test suite**

Run: `pytest -v`
Expected: all tests pass.

**Step 2: Run script-file CLI smoke**

Run: `python src/main.py --script-file docs/examples/sample-script.md`
Expected: output video created under `assets/outputs/...`.

**Step 3: Run upload path dry verification**

Run: `pytest tests/test_uploader.py -v`
Expected: uploader logic is covered without requiring real network calls.
