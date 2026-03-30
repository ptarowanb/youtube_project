# Phase 1 Bootstrap Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a runnable Phase 1 project skeleton that can load channel settings, generate a normalized script, synthesize segment audio, and render a basic MP4 through `python src/main.py`.

**Architecture:** Use an expandable monolithic layout under `src/` with explicit module boundaries for current and future pipeline stages. Keep Phase 1 orchestration synchronous in `src/main.py`, while preserving interfaces for later queue-driven expansion.

**Tech Stack:** Python 3.10+, pytest, PyYAML, python-dotenv, MoviePy, edge-tts, pydub, OpenAI SDK

---

### Task 1: Create project skeleton and dependencies

**Files:**
- Create: `src/__init__.py`
- Create: `src/utils/__init__.py`
- Create: `assets/.gitkeep`
- Create: `assets/bgm/.gitkeep`
- Create: `assets/outputs/.gitkeep`
- Create: `assets/temp/.gitkeep`
- Create: `database/.gitkeep`
- Create: `configs/channel_settings.yaml`
- Create: `configs/prompts/knowledge.txt`
- Create: `configs/prompts/mystery.txt`
- Create: `configs/prompts/healing.txt`
- Create: `.env.example`
- Create: `requirements.txt`
- Create: `README.md`
- Test: none

**Step 1: Create the directory and placeholder file layout**

Create the paths exactly as listed above so imports and runtime output directories are stable from the first commit.

**Step 2: Write baseline configuration artifacts**

Add:
- three channels in `configs/channel_settings.yaml`
- prompt template placeholders in `configs/prompts/*.txt`
- environment variable examples in `.env.example`
- dependency list in `requirements.txt`

**Step 3: Document the bootstrap flow**

Add a concise `README.md` with setup, CLI usage, and fallback behavior notes.

**Step 4: Verify file layout**

Run: `Get-ChildItem -Recurse src,configs,assets,database`
Expected: all planned paths exist.

### Task 2: Add domain models, validation helpers, and config loading with TDD

**Files:**
- Create: `src/models.py`
- Create: `src/config_loader.py`
- Create: `src/utils/validators.py`
- Create: `tests/test_config_loader.py`

**Step 1: Write the failing test**

Write tests for:
- loading known channel settings with `defaults` merged
- returning only enabled channels
- rejecting unknown channels
- rejecting explicitly disabled channels when requested

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_config_loader.py -v`
Expected: FAIL because loader module does not exist yet.

**Step 3: Write minimal implementation**

Implement:
- shared dataclasses in `src/models.py`
- YAML loading and merge logic in `src/config_loader.py`
- small validation helpers in `src/utils/validators.py`

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_config_loader.py -v`
Expected: PASS

### Task 3: Add script generation with deterministic fallback using TDD

**Files:**
- Create: `src/scripter.py`
- Create: `tests/test_scripter.py`

**Step 1: Write the failing test**

Cover:
- fallback script generation returns normalized payload with 3+ segments
- channel and topic are reflected in the payload
- segment IDs are sequential

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_scripter.py -v`
Expected: FAIL because `src/scripter.py` does not exist yet.

**Step 3: Write minimal implementation**

Implement:
- prompt file resolution
- `generate_script(topic, channel, channel_config, use_openai=True)`
- offline fallback path when API key is missing
- JSON save helper for run output

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_scripter.py -v`
Expected: PASS

### Task 4: Add audio generation abstraction with test-friendly fallback using TDD

**Files:**
- Create: `src/voice_gen.py`
- Create: `tests/test_voice_gen.py`

**Step 1: Write the failing test**

Cover:
- generating one audio artifact per segment
- preserving segment order in returned paths
- creating files in the expected output directory

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_voice_gen.py -v`
Expected: FAIL because `src/voice_gen.py` does not exist yet.

**Step 3: Write minimal implementation**

Implement:
- provider abstraction for real `edge-tts` and local fallback
- batch generation helper returning ordered `Path` list
- safe fallback path used in tests when external tools are unavailable

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_voice_gen.py -v`
Expected: PASS

### Task 5: Add editor and basic subtitle overlay using TDD

**Files:**
- Create: `src/editor.py`
- Create: `tests/test_editor.py`

**Step 1: Write the failing test**

Cover:
- editor rejects mismatched segment/audio counts
- editor plans an output path under the requested run directory
- lightweight smoke path can assemble clip metadata without rendering full video in tests

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_editor.py -v`
Expected: FAIL because `src/editor.py` does not exist yet.

**Step 3: Write minimal implementation**

Implement:
- clip planning helper for testable pure logic
- simple visual composition
- subtitle text overlay
- final render function guarded so unit tests can avoid expensive full render

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_editor.py -v`
Expected: PASS

### Task 6: Add pipeline orchestration CLI using TDD

**Files:**
- Create: `src/main.py`
- Create: `tests/test_main.py`

**Step 1: Write the failing test**

Cover:
- parsing `--topic` and `--channel`
- `--list-channels` output behavior
- orchestration calling config, script, audio, and editor stages in order with fakes

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_main.py -v`
Expected: FAIL because `src/main.py` does not exist yet.

**Step 3: Write minimal implementation**

Implement:
- CLI parser
- run directory creation
- single-channel execution path
- all-channel execution path

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_main.py -v`
Expected: PASS

### Task 7: Add future-stage module stubs

**Files:**
- Create: `src/subtitle_gen.py`
- Create: `src/asset_manager.py`
- Create: `src/job_tracker.py`
- Create: `src/scheduler.py`
- Create: `src/uploader.py`
- Create: `src/utils/logger.py`
- Create: `tests/test_module_stubs.py`

**Step 1: Write the failing test**

Cover:
- modules are importable
- public interfaces exist
- intentionally unfinished modules fail in a clear, targeted way where applicable

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_module_stubs.py -v`
Expected: FAIL because the stub modules do not exist yet.

**Step 3: Write minimal implementation**

Implement stable import paths and public placeholders aligned with `docs/ARCHITECTURE.md`.

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_module_stubs.py -v`
Expected: PASS

### Task 8: Verify the full Phase 1 baseline

**Files:**
- Modify as needed based on failures from earlier tasks

**Step 1: Install dependencies**

Run: `python -m pip install -r requirements.txt`
Expected: dependencies install successfully.

**Step 2: Run the full test suite**

Run: `pytest -v`
Expected: all tests pass.

**Step 3: Perform CLI smoke verification**

Run: `python src/main.py --list-channels`
Expected: enabled channel IDs are printed.

**Step 4: Perform end-to-end local run**

Run: `python src/main.py --topic "ChatGPT 활용법" --channel knowledge`
Expected: run directory created under `assets/outputs/knowledge/<date>/...` and video output path printed. If external providers are unavailable, fallback behavior should still complete with documented limitations.

**Step 5: Record residual gaps**

Update `README.md` if the environment requires `ffmpeg`, `edge-tts`, or OpenAI credentials for non-fallback behavior.
