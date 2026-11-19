# Project instructions for coding agents

Read `docs/TV3_HANDOFF.md`, `docs/API_CONTRACT.md` and `CONTRIBUTING.md` before integrating TV3 work. The combined handoff branch is `feat/tv3-handoff`. `feat/cong-tuan-ui-loadtest` stays at its previous revision; do not push this handoff into that branch without a new user request.

## Boundaries

- `app/`: backend/data owned by TV2. This handoff does not change its API/schema. Upload is a raw byte body, not multipart. Verify HTTP 200 can contain `intact=false`, which is an integrity failure.
- `frontend/`: static UI owned by TV3. Preserve progress/cancel, uncertain upload messages, stale-list protection and pagination, hash copy, and detailed verification. No package install/build is required.
- `loadtest/`: TV3 validation and workload. Preserve `LOADTEST_FILE_ID`, streaming SHA-256/byte counting, semantic failures, fail-fast fixture setup and final counters. Tasks must not repeatedly upload files.
- `deploy/elasticity/`: TV3 preparation coordinated with TV1. JSON (`kit.py`, root `*.json`, `probe_http.py`) is the current handoff path. The previous YAML tools remain for existing users; see `YAML_RUNBOOK.md`. Never mix their parameters or deploy both against the same managed resources.

## Verification

Use Node.js 20+ and Docker Linux containers. Keep an existing `.env`; create it from `.env.example` only when absent. Build with `docker compose up --build -d --wait --wait-timeout 180`. Run the commands in `docs/TV3_HANDOFF.md` or `scripts/test.ps1` (PowerShell). The standalone YAML suite needs its separate validation dependencies; do not add them to the application lock only for tooling.

API tests use temporary storage. Live smoke creates one labelled synthetic file. Keep assertions for negative HTTP/semantic cases. Do not remove tests or weaken validation to obtain a passing build. Local or mocked success is not OpenStack deployment evidence.

## Integration and credentials

Work in a feature/integration branch. Preserve teammates' changes and resolve conflicting interfaces deliberately; never blanket replace their backend, Compose or workflow files. Never delete database/file volumes as a way to integrate code. OpenStack alarms default off; actual cloud resource changes need the user's authorization and verified group inputs.

Do not commit `.env`, `app.env`, generated `*.env.json`, private YAML, cloud credentials, SSH keys, database dumps, uploads, local runtimes or raw test-results. Existing evidence under `docs/evidence/` is synthetic and scoped to its recorded commit/date. Read access to any online account does not authorize writes; push/PR/merge/account changes require the user's applicable authorization.
