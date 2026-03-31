# Backend

FastAPI backend for Sketch-to-Cloud.

## Run
```powershell
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## Core Directories
- `app/`: API routers, services, schemas
- `alembic/`: DB migrations
- `tests/`: pytest suites
- `scripts/`: smoke checks and evaluation scripts
- `evals/`: golden/real evaluation datasets

## Repo Analysis Mode (AI-Only)
Set these env values to force Bedrock-only GitHub repo analysis:

```env
BEDROCK_ENABLED=true
BEDROCK_STRICT_MODE=true
BEDROCK_FALLBACK_ENABLED=false
GITHUB_REPO_ANALYSIS_AI_ONLY=true
```

If any of these are violated, `/api/github/repo-analysis` returns `503`.

Auth endpoint rate limit (defaults):
```env
AUTH_RATE_LIMIT=20
AUTH_RATE_LIMIT_WINDOW_SECONDS=60
```

Core middleware:
- `X-Request-ID` response header
- Structured access logs (JSON line per request)
- Security headers (`nosniff`, `DENY`, CSP, Referrer-Policy)
- `/api/auth/login`, `/api/auth/register` in-memory rate limiting
- Error responses include `requestId` for tracing

Operational status endpoint:
- `GET /api/ops/repo-analysis-health` (auth required)
- Returns AI-only policy readiness, cache stats, recent failure summary, and recommendations
- `GET /api/ops/readiness` (auth required, readiness score/grade/checklist)
- `GET /api/github/status` (auth required, OAuth/token/API 연결 상태 점검)
- `POST /api/ops/repo-analysis-feedback` (auth required, `APPROVE|HOLD`)
- `GET /api/ops/repo-analysis-feedback?fullName=owner/repo` (auth required)

## Test Commands
```powershell
cd backend
pytest -q
python scripts/smoke_api_testclient.py
python scripts/eval_repo_analysis.py --min-score 0.75
python scripts/eval_cost_sanity.py
python scripts/preflight_check.py --skip-smoke
python scripts/security_baseline_check.py
```

## Optional Real-Repo Eval
```powershell
cd backend
python scripts/build_real_repo_eval_dataset.py --repos owner1/repo1 owner2/repo2
python scripts/preflight_check.py --skip-smoke --run-real-eval --real-min-score 0.70
```
