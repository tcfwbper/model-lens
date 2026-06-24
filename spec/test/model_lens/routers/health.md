# Test Specification: `test_health.py`

## Source File Under Test
`src/model_lens/routers/health.py`

## Test File
`tests/model_lens/routers/test_health.py`

---

## `GET /healthz`

### Happy Path — GET /healthz

| Test ID | Category | Description | Setup | Input | Expected |
|---|---|---|---|---|---|
| `test_healthz_returns_200` | `unit` | Returns 200 with empty body. | Create a `TestClient` from a FastAPI app that includes `health.router`. Set `app.state.pipeline` to a mock to bypass lifespan. | `GET /healthz` | Response status code is `200`; response body is empty |
