# automation CI/CD Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a GitHub Actions pipeline that builds and deploys the private `automation` ECS service on every push to `main`.

**Architecture:** The repository will include a minimal Python HTTP service for `automation`, a Docker image definition, and a GitHub Actions workflow. The workflow builds the image, pushes it to ECR with an immutable SHA tag, renders a new ECS task definition revision for container `automation`, and rolls the `automation` service in cluster `n8n`.

**Tech Stack:** Python stdlib HTTP server, pytest, Docker, GitHub Actions, AWS ECR, AWS ECS, Terraform.

---

### Task 1: Document the CI/CD design

**Files:**
- Create: `docs/plans/2026-04-07-automation-cicd-design.md`
- Create: `docs/plans/2026-04-07-automation-cicd.md`

**Step 1: Capture the approved design**

- Write the CI/CD scope, workflow, and health-check decisions into the design doc.

**Step 2: Capture the implementation sequence**

- Write the concrete file-level plan into the implementation plan.

### Task 2: Add a failing test for the automation service

**Files:**
- Create: `tests/test_automation_server.py`
- Create: `src/__init__.py`
- Create: `src/automation_server.py`

**Step 1: Write the failing test**

- Add tests for:
  - `GET /health` returns `200`
  - `POST /render-jobs` rejects missing auth token
  - `POST /render-jobs` accepts a valid request and creates a job
  - `GET /render-jobs/{id}` returns stored job state

**Step 2: Run the test and verify failure**

Run: `pytest tests/test_automation_server.py -q`

Expected: failure because `src.automation_server` does not exist yet.

### Task 3: Implement the minimal automation service

**Files:**
- Create: `src/automation_server.py`
- Create: `src/__init__.py`

**Step 1: Add the smallest service that satisfies the tests**

- Implement a stdlib HTTP server with:
  - `GET /health`
  - `POST /render-jobs`
  - `GET /render-jobs/{job_id}`
- Use an in-memory job store for now.
- Require `X-Automation-Token` on render job creation.

**Step 2: Run the tests and verify pass**

Run: `pytest tests/test_automation_server.py -q`

Expected: all tests pass.

### Task 4: Add the container build assets

**Files:**
- Create: `Dockerfile`
- Create: `.dockerignore`

**Step 1: Add a runtime Dockerfile**

- Use a Python slim base image.
- Install `ffmpeg`.
- Install `requirements.txt`.
- Launch the service with `python -m src.automation_server`.
- Do not add Dockerfile `HEALTHCHECK`.

**Step 2: Verify the image builds**

Run: `docker build -t automation-local .`

Expected: successful image build.

### Task 5: Add GitHub Actions deployment workflow

**Files:**
- Create: `.github/workflows/deploy-automation.yml`

**Step 1: Add the workflow**

- Trigger on pushes to `main`.
- Configure AWS credentials from GitHub secrets.
- Log in to ECR.
- Build and push `project1:${{ github.sha }}`.
- Fetch the current ECS task definition.
- Replace only the `automation` container image.
- Register the new revision and deploy it to service `automation` in cluster `n8n`.

**Step 2: Verify workflow structure locally**

- Inspect the YAML file.
- Confirm referenced secret names and AWS identifiers are correct.

### Task 6: Update Terraform health checks and docs

**Files:**
- Modify: `terraform/ecs.tf`
- Modify: `terraform/README.md`
- Modify: `README.md`

**Step 1: Add ECS container health checks consistently**

- Keep the existing `automation` ECS health check.
- Add a task-definition-level health check to `n8n`.

**Step 2: Update docs**

- Describe the GitHub Actions workflow and required repository secrets.

### Task 7: Final verification

**Files:**
- Verify all touched files

**Step 1: Run Python tests**

Run: `pytest tests/test_automation_server.py -q`

**Step 2: Run Terraform validation**

Run: `$env:AWS_PROFILE='runner'; terraform -chdir=terraform validate`

**Step 3: Build the Docker image if Docker is available**

Run: `docker build -t automation-local .`

**Step 4: Review git diff**

Run: `git diff -- . ':(exclude)terraform/.terraform'`
