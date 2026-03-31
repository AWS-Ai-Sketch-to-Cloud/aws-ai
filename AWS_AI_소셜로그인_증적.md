# AWS_AI 소셜로그인 증적

## 1. 작업 개요

- 대상 프로젝트: `aws-ai`
- 작업 목적: Sketch-to-Cloud 프로젝트 로그인 화면에 소셜 로그인 기능을 연동하고, 백엔드 OAuth 처리와 프론트 콜백 흐름을 실제 프로젝트 구조에 맞게 연결
- 지원 provider:
  - `google`
  - `naver`
  - `kakao`
  - `github`
- 적용 범위:
  - 로그인 페이지 소셜 로그인 버튼 4종 추가
  - 백엔드 OAuth 시작/콜백/자동가입 완료 API 추가
  - 프론트 콜백 페이지 추가 및 `sessionStorage` 기반 세션 저장 처리
  - 미등록 소셜 계정에 대해 확인 모달 후 자동 가입 처리
  - GitHub 로그인 성공 시 OAuth access token 암호화 저장

## 2. 프로젝트 기준 구현 결과

### 프론트엔드

- 로그인 화면에 네이버, 구글, 카카오, GitHub 로그인 버튼 추가
- GitHub 버튼에는 레포지토리 연동 안내 툴팁 표시
- 소셜 로그인 시작 시 백엔드 `/api/auth/social/{provider}/start`로 이동
- 콜백 전용 페이지 `/auth/social/callback` 추가
- 백엔드가 URL fragment(`#payload=...`, `#signup=...`, `#error=...`)로 전달한 결과를 파싱
- 로그인 성공 시 `sessionStorage`의 `stc-auth`에 세션 저장 후 `/dashboard` 이동
- 미등록 소셜 계정은 자동 가입 전에 확인 모달 표시

### 백엔드

- 소셜 로그인 시작 API 추가
  - `GET /api/auth/social/{provider}/start`
- 소셜 로그인 콜백 API 추가
  - `GET /api/auth/social/{provider}/callback`
- 자동 가입 완료 API 추가
  - `POST /api/auth/social/complete-signup`
- 지원 provider 검증 및 state 기반 요청 검증 처리
- provider별 access token 교환 및 사용자 프로필 조회 처리
- 기존 계정 식별 시 즉시 로그인 세션 발급
- 미등록 계정은 signup payload를 프론트로 전달
- GitHub 로그인 성공 시 `github_oauth_tokens` 테이블에 access token 암호화 저장

### 데이터베이스

- `auth_identities.provider` 허용값 확장
  - 기존: `LOCAL`, `GOOGLE`, `GITHUB`
  - 변경 후: `LOCAL`, `GOOGLE`, `GITHUB`, `NAVER`, `KAKAO`
- GitHub OAuth token 저장용 `github_oauth_tokens` 테이블 추가
- 로컬 계정과 소셜 계정을 동일 `users` / `auth_identities` 구조에서 통합 관리

## 3. 실제 반영 파일

### 백엔드

- `backend/app/routers/auth.py`
- `backend/app/schemas/auth.py`
- `backend/app/services/github_oauth_store.py`
- `backend/app/models.py`
- `backend/db/schema_v1.sql`
- `backend/alembic/versions/6b1f2f6a3f0c_add_naver_kakao_auth_providers.py`
- `backend/alembic/versions/d4e5f6a7b8c9_add_github_oauth_tokens_table.py`

### 프론트엔드

- `frontend/app/src/pages/Auth/LoginPage.tsx`
- `frontend/app/src/pages/Auth/SocialCallbackPage.tsx`
- `frontend/app/src/pages/Auth/SignupPage.tsx`
- `frontend/app/src/lib/auth-session.ts`
- `frontend/app/src/App.tsx`

### 환경 설정

- `.env`

## 4. 현재 프로젝트 기준 OAuth 동작 방식

### 공통 흐름

1. 사용자가 로그인 페이지에서 소셜 로그인 버튼 클릭
2. 프론트가 백엔드 `/api/auth/social/{provider}/start`로 이동
3. 백엔드가 provider 인증 페이지로 redirect
4. 인증 완료 후 provider가 백엔드 callback URL 호출
5. 백엔드가 access token 교환 후 사용자 프로필 조회
6. 기존 계정 여부 판단
7. 결과를 프론트 콜백 페이지(`/auth/social/callback`)로 fragment 형태로 전달
8. 프론트가 결과를 파싱하여 세션 저장 또는 자동 가입 진행

### 기존 계정인 경우

- `auth_identities`에 동일 provider + provider_user_id가 있으면 즉시 로그인 처리
- 동일 이메일의 기존 사용자만 있고 해당 provider 연결이 없으면 identity를 추가 연결한 뒤 로그인 처리
- 로그인 성공 시 access token / refresh token 발급

### 미등록 소셜 계정인 경우

- 백엔드는 즉시 가입시키지 않고 `signup` payload를 프론트로 전달
- 프론트 콜백 페이지에서 확인 모달 표시
- 사용자가 `네, 계속 진행` 선택 시 `/api/auth/social/complete-signup` 호출
- 자동 가입 완료 후 바로 로그인 세션 저장

## 5. 현재 코드 기준 API

### 인증 기본 API

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/users/me`

### 소셜 로그인 API

- `GET /api/auth/social/{provider}/start`
- `GET /api/auth/social/{provider}/callback`
- `POST /api/auth/social/complete-signup`

### 지원 provider

- `google`
- `naver`
- `kakao`
- `github`

## 6. 환경변수 정리

프로젝트에서 실제 사용하는 소셜 로그인 관련 환경변수는 아래와 같다.

```env
SOCIAL_LOGIN_REDIRECT_URL=http://localhost:5173/auth/social/callback

GOOGLE_OAUTH_CLIENT_ID=
GOOGLE_OAUTH_CLIENT_SECRET=

NAVER_OAUTH_CLIENT_ID=
NAVER_OAUTH_CLIENT_SECRET=

KAKAO_OAUTH_CLIENT_ID=
KAKAO_OAUTH_CLIENT_SECRET=

GITHUB_OAUTH_CLIENT_ID=
GITHUB_OAUTH_CLIENT_SECRET=
GITHUB_TOKEN_ENCRYPTION_KEY=
```

설명:

- `SOCIAL_LOGIN_REDIRECT_URL`
  - 백엔드 callback 처리 후 프론트 콜백 페이지로 redirect할 주소
- `*_OAUTH_CLIENT_ID`, `*_OAUTH_CLIENT_SECRET`
  - 각 provider 콘솔에서 발급받은 OAuth 앱 정보
- `GITHUB_TOKEN_ENCRYPTION_KEY`
  - GitHub access token 저장 시 암호화용 키

참고:

- 백엔드는 `backend/.env`와 repo root `.env`를 모두 읽도록 구현되어 있음
- 프론트 기본 API 주소는 `VITE_API_BASE_URL` 미설정 시 `http://127.0.0.1:8000`

## 7. Provider 콘솔 등록 기준

### 프론트 주소

- `http://127.0.0.1:5173`
- `http://localhost:5173`

### 백엔드 callback 주소

- Google:
  - `http://127.0.0.1:8000/api/auth/social/google/callback`
  - 필요 시 `http://localhost:8000/api/auth/social/google/callback`
- Naver:
  - `http://127.0.0.1:8000/api/auth/social/naver/callback`
  - 필요 시 `http://localhost:8000/api/auth/social/naver/callback`
- Kakao:
  - `http://127.0.0.1:8000/api/auth/social/kakao/callback`
  - 필요 시 `http://localhost:8000/api/auth/social/kakao/callback`
- GitHub:
  - `http://127.0.0.1:8000/api/auth/social/github/callback`
  - 필요 시 `http://localhost:8000/api/auth/social/github/callback`

주의:

- Provider 콘솔에 등록하는 주소는 백엔드 callback URL
- `.env`의 `SOCIAL_LOGIN_REDIRECT_URL`은 프론트 콜백 페이지 주소
- 두 주소는 역할이 다르므로 혼동하면 안 됨

## 8. 구현 중 확인된 이슈와 반영 내용

### 8-1. provider 허용값 제약 문제

- 기존 DB 체크 제약에는 `NAVER`, `KAKAO`가 포함되지 않음
- 소셜 로그인 연동 과정에서 `auth_identities_provider_check` 제약 오류 가능성 확인
- Alembic migration과 `schema_v1.sql`을 함께 수정하여 허용값 확장

### 8-2. 프론트 callback 주소와 provider callback 주소 분리

- Provider는 백엔드 callback으로 돌아와야 함
- 백엔드가 최종적으로 프론트 `SOCIAL_LOGIN_REDIRECT_URL`로 다시 redirect하는 구조임
- 이 역할을 분리하지 않으면 OAuth 설정 오류가 발생함

### 8-3. GitHub 프로필 정보 보강

- GitHub는 `/user` 응답에 `email` 또는 `name`이 비어 있을 수 있음
- 코드에서 다음 우선순위로 보강 처리
  - display name: `name` -> `login` -> 이메일 앞부분
  - email: `/user` 값 우선, 없으면 `/user/emails` 추가 조회

### 8-4. 미등록 소셜 계정 가입 UX 조정

- 자동으로 바로 가입시키지 않고 사용자 확인 모달을 거치도록 구현
- 현재 프로젝트의 실제 UX는 “확인 후 자동 가입” 방식

### 8-5. GitHub 토큰 저장

- GitHub 로그인 성공 시 access token을 세션 처리와 별개로 DB에도 저장
- `github_oauth_tokens` 테이블에 암호화 저장
- 이후 GitHub 저장소 분석 기능과 연계 가능한 구조로 반영됨

## 9. 실행 및 반영 절차

### 백엔드

```powershell
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --reload
```

### 프론트엔드

```powershell
cd frontend/app
npm install
npm run dev
```

## 10. 검증 기준

- 로그인 페이지에서 소셜 로그인 버튼 4종 노출 확인
- 각 provider 시작 URL이 정상 생성되는지 확인
- provider 인증 후 백엔드 callback 진입 확인
- 성공 시 프론트 콜백 페이지로 `#payload=` 또는 `#signup=` 전달 확인
- 기존 계정은 즉시 로그인 후 `/dashboard` 이동 확인
- 미등록 계정은 확인 모달 표시 후 자동 가입 및 로그인 확인
- GitHub 로그인 성공 시 토큰 저장 로직 반영 확인
- 프론트 라우팅에 `/auth/social/callback` 등록 확인
- DB 스키마에 `NAVER`, `KAKAO`, `github_oauth_tokens` 반영 확인

## 11. 현재 상태

- 네이버, 구글, 카카오, GitHub 소셜 로그인 코드 반영 완료
- 프론트/백엔드 OAuth 흐름 연결 완료
- 자동 가입 확인 모달 방식 반영 완료
- GitHub OAuth token 저장 구조 반영 완료
- DB 반영을 위해 Alembic migration 적용 필요

## 12. 후속 확인 권장 사항

- 운영 도메인 기준 redirect URI 별도 등록
- provider별 동의 항목과 이메일 제공 여부 재점검
- `127.0.0.1`과 `localhost` 사용 기준 통일
- 실제 OAuth 연동 테스트 계정 기준 최종 점검
