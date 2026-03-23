# API 스모크 테스트 (v2)

목적:
- 팀원이 같은 순서로 v2 API 동작을 빠르게 확인
- 흐름: `auth -> upload -> project -> session -> status -> architecture -> terraform -> cost -> detail -> logout`

전제:
- 서버 실행: `uvicorn app.main:app --reload`
- 기본 주소: `http://127.0.0.1:8000`
- DB에 `users.login_id` 컬럼이 반영되어 있어야 함
  - 미반영 시 [schema_v1.sql](/c:/Users/junse/Desktop/vscode/team-project/aws-ai/backend/db/schema_v1.sql) 재실행

## 자동 실행(권장)

```powershell
cd backend
./scripts/smoke_api.ps1
```

## 수동 실행 순서

1) `POST /api/auth/register`
- 사용자 생성, 기대: `contractVersion = "v2"`

2) `POST /api/auth/login`
- 기대: `accessToken`, `refreshToken` 반환

3) `GET /api/users/me`
- 헤더: `Authorization: Bearer {accessToken}`

4) `POST /api/uploads/images`
- 현재는 URL 발급 스텁 동작

5) `POST /api/projects`

6) `POST /api/projects/{projectId}/sessions`

7) `PATCH /api/sessions/{sessionId}/status`

8) `POST /api/sessions/{sessionId}/architecture`

9) `POST /api/sessions/{sessionId}/terraform`
- 기대: `status=GENERATED`, `contractVersion="v2"`

10) `POST /api/sessions/{sessionId}/cost`
- 기대: `status=COST_CALCULATED`, `contractVersion="v2"`

11) `GET /api/sessions/{sessionId}`
- 기대: `architecture/terraform/cost` 모두 존재

12) `POST /api/auth/logout`
- 기대: `success=true`, `contractVersion="v2"`
