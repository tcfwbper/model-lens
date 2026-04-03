# ModelLens

A lightweight AI demo tool that streams frames from a camera source, runs object detection on each frame, and exposes a browser-based UI for live configuration — without restarting the server.

**Stack:** Python 3.11 · FastAPI · Ultralytics (YOLOv8) · React 19 · TypeScript · Vite

---

## Table of Contents

- [Features](#features)
- [Setup](#setup)
  - [Install from PyPI](#install-from-pypi)
  - [Development Setup](#development-setup)
    - [System Prerequisites](#system-prerequisites)
    - [Python Environment](#python-environment)
    - [Node.js Environment](#nodejs-environment)
- [Running the Server](#running-the-server)
- [Development Commands](#development-commands)
- [Configuration](#configuration)
- [Dev Workflow](#dev-workflow)
- [Contribution](#contribution)

---

## Features

- Live camera stream (local webcam or RTSP/IP camera)
- Real-time object detection overlay via bundled YOLOv8 model
- Browser UI to update camera source and target labels at runtime
- SSE-based frame streaming — no page refresh required
- Runtime config via TOML file or environment variables

---

## Setup

### Install from PyPI

```bash
pip install model-lens
model_lens --host=0.0.0.0 --port=8080
```

### Development Setup

#### System Prerequisites

Install the following system packages (Debian/Ubuntu):

```bash
apt-get install -y python3.11 python3.11-venv
```

Install **uv** (Python package manager):

```bash
bash dev/uv-install.sh
```

#### Python Environment

Create and populate the virtual environment:

```bash
bash dev/venv-create.sh          # creates .venv using python3.11
. .venv/bin/activate
bash dev/bootstrap.sh            # installs all Python dependencies (editable + dev)
```

Run format checks and unit tests to verify the setup:

```bash
bash dev/format-and-test.sh
```

To also run E2E and race condition tests (same as CI):

```bash
bash dev/format-and-test.sh --all
```

#### Node.js Environment

Install **nvm** and the required Node.js version (specified in `.nvmrc`, currently `20`):

```bash
bash dev/nvm-install.sh
export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh"
bash dev/ui-install.sh           # runs nvm install + npm install
```

Run frontend tests:

```bash
bash dev/ui-test.sh
```

Build static assets (required before running the server):

```bash
bash dev/ui-build.sh
```

---

## Running the Server

```bash
. .venv/bin/activate
bash dev/model-lens-runs.sh
```

The server starts at `http://0.0.0.0:8080` by default.

Custom host/port:

```bash
bash dev/model-lens-runs.sh --host=127.0.0.1 --port=9000
```

---

## Development Commands

| Command | Purpose |
|---|---|
| `dev/venv-create.sh` | Create Python virtual environment (`.venv`) |
| `dev/bootstrap.sh` | Install all Python dependencies |
| `dev/format.sh` | Run black, isort, docformatter |
| `dev/test.sh` | Run unit tests only |
| `dev/test.sh --all` | Run full test suite (unit + E2E + race) |
| `dev/format-and-test.sh` | Format then run unit tests |
| `dev/format-and-test.sh --all` | Format then run full test suite |
| `dev/nvm-install.sh` | Install nvm |
| `dev/ui-install.sh` | Install Node.js dependencies |
| `dev/ui-test.sh` | Run frontend tests (Vitest) |
| `dev/ui-build.sh` | Build frontend assets into `src/model_lens/dist/` |
| `dev/model-lens-runs.sh` | Start the ModelLens server |

---

## Configuration

Configuration is loaded from a TOML file with environment variable overrides. The file defaults to `model_lens.toml` in the working directory, or can be specified via `--config=<path>`.

### Config File (`model_lens.toml`)

```toml
[server]
host = "0.0.0.0"
port = 8080
log_level = "info"

[camera]
source_type = "local"   # "local" or "rtsp"
device_index = 0
rtsp_url = ""

[model]
model = "yolov8n"
confidence_threshold = 0.5
```

### Environment Variables

All config values can be overridden with environment variables using the `ML_<SECTION>_<KEY>` convention:

| Variable | Default | Description |
|---|---|---|
| `ML_SERVER_HOST` | `0.0.0.0` | Server bind address |
| `ML_SERVER_PORT` | `8080` | Server port |
| `ML_SERVER_LOG_LEVEL` | `info` | Uvicorn log level |
| `ML_CAMERA_SOURCE_TYPE` | `local` | `local` or `rtsp` |
| `ML_CAMERA_DEVICE_INDEX` | `0` | Webcam device index |
| `ML_CAMERA_RTSP_URL` | `` | RTSP stream URL |
| `ML_MODEL_MODEL` | `` | YOLO model |
| `ML_MODEL_CONFIDENCE_THRESHOLD` | `0.5` | Detection confidence threshold |

> **Note:** `[model]` section values are fixed at startup and cannot be changed via the runtime Config API.

---

## Dev Workflow

This project follows **SDD + TDD** (Specification-Driven Development + Test-Driven Development).

```
spec/  →  test/  →  src/
```

1. **Design first** — check `spec/` for a relevant spec before writing any code.
2. **Test second** — write test cases in `test/` that initially fail.
3. **Code last** — implement the minimum code in `src/` to make tests pass.

See [`spec/workflow.md`](spec/workflow.md) for the full workflow and quality gates.

---

## Contribution

1. Fork the repository and create a feature branch.
2. Follow the [Dev Workflow](#dev-workflow) — spec → test → code.
3. Ensure all quality gates pass before opening a PR:
   ```bash
   bash dev/format-and-test.sh
   ```
4. Open a pull request against `main`. CI will run the full test suite (`dev/test.sh --all`) plus a server smoke test.
