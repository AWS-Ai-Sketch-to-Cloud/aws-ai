# backend

백엔드 개발 폴더.

주요 경로:
- `app/`: FastAPI 애플리케이션
- `db/`: SQL 스키마
- `alembic/`: 마이그레이션
- `scripts/`: 운영/검증 스크립트

기본 실행:
```powershell
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload
```

스모크 테스트:
```powershell
cd backend
python scripts/smoke_api_testclient.py
```

회귀 테스트:
```powershell
pytest -q tests/test_sessions_pipeline.py
```

