# Test Specification: `test/model_lens/routers/test_health.md`

## Source File Under Test

`src/model_lens/routers/health.py`

## Test File

`test/model_lens/routers/test_health.py`

## Imports Required

```python
import pytest
from fastapi.testclient import TestClient
```

## Fixtures

Uses the shared `client` and `mock_pipeline` fixtures from `conftest.py`.

---

## 1. Health Check — `GET /healthz`

### 1.1 Happy Path — GET /healthz

| Test ID | Category | Description | Input | Expected |
|---|---|---|---|---|
| `test_healthz_returns_200` | `unit` | `GET /healthz` returns HTTP 200 | `GET /healthz` | `response.status_code == 200` |
| `test_healthz_returns_empty_body` | `unit` | Response body is empty | `GET /healthz` | `response.content == b""` |

---

## Summary Table

| Entity | Test Count (approx.) | unit | e2e | race | Key Concerns |
|---|---|---|---|---|---|
| `GET /healthz` | 2 | 2 | 0 | 0 | 200 status, empty body |
