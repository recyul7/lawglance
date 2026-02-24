# export-policy-gate

## Plan
- [x] Create isolated worktree and verify clean baseline tests
- [x] Bring source policy module/data into worktree (dependency for feature)
- [x] Add API export/download route with policy gate (`is_source_export_allowed`)
- [x] Inject source policy into router from app startup
- [x] Add API tests for allowed and blocked exports
- [x] Run targeted tests and lint checks

## Review
- Added `GET /api/sources/{source_id}/export` with policy enforcement and `POLICY_BLOCKED` error envelope on deny.
- Upgraded successful export response to a registry-backed download manifest (authoritative `download_url`, source metadata, registry version/jurisdiction).
- Added `SOURCE_UNAVAILABLE` (404) behavior when policy allows export but registry metadata is missing.
- Injected `SourcePolicy` into the cases router via `create_app()` startup wiring.
- Injected `SourceRegistry` into the cases router via `create_app()` startup wiring.
- Added allow/deny API contract tests and verified full suite passes.
- Repo-wide lint still has unrelated pre-existing issues outside changed files; changed files pass Ruff checks.
