# AWS AI 소셜로그인 증적

## 1. 작업 개요

- 대상 프로젝트: `aws-ai`
- 작업 목적: 로그인 페이지에 소셜 로그인 UI를 추가하고 `네이버 / 구글 / 카카오 / 깃허브` OAuth 로그인을 연동
- 구현 범위:
  - 로그인 페이지에 소셜 로그인 버튼 4종 추가
  - 실제 연동 대상:
    - `네이버`
    - `구글`
    - `카카오`
    - `깃허브`
  - 소셜 로그인 성공 시 기존 로그인과 동일한 세션 저장 방식 적용
  - 미등록 소셜 계정은 자동가입 전 확인 모달을 거친 뒤 가입 및 로그인 진행

## 2. 구현 완료 항목

### 프론트엔드

- 로그인 페이지에 소셜 로그인 버튼 추가
  - `네이버 로그인`
  - `구글 로그인`
  - `카카오톡 로그인`
  - `깃허브 로그인`
- 각 버튼 왼쪽에 플랫폼 로고 추가
- 일반 로그인 버튼 아래로 소셜 로그인 버튼 재배치
- 회원가입 유도 문구 수정
  - `아직 회원이 아니신가요? 회원가입`
- 소셜 로그인 콜백 페이지 추가
- 소셜 계정이 미등록 상태일 경우 자동가입 전 확인 모달 표시
- 확인 모달에서 `네, 계속 진행` 선택 시 자동가입 후 바로 로그인

### 백엔드

- 소셜 로그인 시작 엔드포인트 추가
  - `GET /api/auth/social/{provider}/start`
- 소셜 로그인 콜백 엔드포인트 추가
  - `GET /api/auth/social/{provider}/callback`
- 자동가입 완료 엔드포인트 추가
  - `POST /api/auth/social/complete-signup`
- 지원 provider
  - `google`
  - `naver`
  - `kakao`
  - `github`
- 기존 계정이 존재하면 바로 로그인
- 미등록 소셜 계정은 가입 필요 payload를 프론트로 전달
- 사용자가 확인하면 자동가입 처리 후 로그인 세션 발급

## 3. 수정 파일

### 백엔드

- `backend/app/routers/auth.py`
- `backend/app/schemas/auth.py`
- `backend/db/schema_v1.sql`
- `backend/alembic/versions/6b1f2f6a3f0c_add_naver_kakao_auth_providers.py`

### 프론트엔드

- `frontend/app/src/pages/Auth/LoginPage.tsx`
- `frontend/app/src/pages/Auth/SocialCallbackPage.tsx`
- `frontend/app/src/pages/Auth/SignupPage.tsx`
- `frontend/app/src/lib/auth-session.ts`
- `frontend/app/src/App.tsx`

### 환경설정

- `.env`

## 4. 환경변수

`.env` 사용 항목:

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
```

각 값의 의미:

- `SOCIAL_LOGIN_REDIRECT_URL`
  - 소셜 로그인 완료 후 백엔드가 프론트 콜백 페이지로 리다이렉트할 주소
- `GOOGLE_OAUTH_CLIENT_ID`
  - Google Cloud OAuth Client ID
- `GOOGLE_OAUTH_CLIENT_SECRET`
  - Google Cloud OAuth Client Secret
- `NAVER_OAUTH_CLIENT_ID`
  - 네이버 개발자센터 Client ID
- `NAVER_OAUTH_CLIENT_SECRET`
  - 네이버 개발자센터 Client Secret
- `KAKAO_OAUTH_CLIENT_ID`
  - Kakao Developers `REST API 키`
- `KAKAO_OAUTH_CLIENT_SECRET`
  - Kakao Developers `Client Secret`
- `GITHUB_OAUTH_CLIENT_ID`
  - GitHub OAuth App Client ID
- `GITHUB_OAUTH_CLIENT_SECRET`
  - GitHub OAuth App Client Secret

## 5. 제공자별 콘솔 등록 정보

### Google

- 승인된 Redirect URI
  - `http://127.0.0.1:8000/api/auth/social/google/callback`
  - 필요 시 `http://localhost:8000/api/auth/social/google/callback`

### Naver

- 서비스 URL
  - `http://127.0.0.1:5173`
  - 필요 시 `http://localhost:5173`
- Callback URL
  - `http://127.0.0.1:8000/api/auth/social/naver/callback`
  - 필요 시 `http://localhost:8000/api/auth/social/naver/callback`
- 개발 중 상태에서는 테스트 ID 등록 가능

### Kakao

- Web 플랫폼 도메인
  - `http://127.0.0.1:5173`
  - `http://localhost:5173`
- Redirect URI
  - `http://127.0.0.1:8000/api/auth/social/kakao/callback`
  - 필요 시 `http://localhost:8000/api/auth/social/kakao/callback`
- 사용 키
  - `REST API 키`
- 사용하지 않는 키
  - `어드민 키`

### GitHub

- OAuth App 등록 위치
  - `Settings > Developer settings > OAuth Apps > New OAuth App`
- Homepage URL
  - `http://127.0.0.1:5173`
- Authorization callback URL
  - `http://127.0.0.1:8000/api/auth/social/github/callback`
  - 필요 시 `http://localhost:8000/api/auth/social/github/callback`
- 발급값
  - `Client ID` -> `GITHUB_OAUTH_CLIENT_ID`
  - `Client Secret` -> `GITHUB_OAUTH_CLIENT_SECRET`

## 6. 동작 방식

### 일반 소셜 로그인

1. 사용자가 로그인 페이지에서 소셜 로그인 버튼 클릭
2. 프론트가 백엔드 `/api/auth/social/{provider}/start`로 이동
3. 백엔드가 각 provider 인증 페이지로 리다이렉트
4. 인증 완료 후 provider가 백엔드 callback URL 호출
5. 백엔드가 사용자 정보 조회
6. 기존 계정이 있으면 로그인 처리
7. 프론트 콜백 페이지로 결과 전달
8. 프론트가 `sessionStorage`에 인증정보 저장 후 `/dashboard` 이동

### 미등록 소셜 계정 자동가입 흐름

1. 소셜 인증은 성공했지만 DB에 연결된 계정이 없음
2. 백엔드가 가입 필요 payload를 프론트 콜백으로 전달
3. 프론트가 확인 모달 표시
4. 사용자가 `네, 계속 진행` 선택
5. 프론트가 `POST /api/auth/social/complete-signup` 호출
6. 백엔드가 자동가입 처리 후 로그인 세션 발급
7. 프론트가 세션 저장 후 `/dashboard` 이동

## 7. 디버깅 및 해결 내역

### 7-1. 네이버 개발자센터 URL 설정 확인

- 실제 브라우저 접속 주소 확인 결과 `127.0.0.1` 기준으로 동작함
- 네이버 등록값도 아래와 같이 `127.0.0.1` 기준으로 맞춰야 정상 동작
  - 서비스 URL: `http://127.0.0.1:5173`
  - Callback URL: `http://127.0.0.1:8000/api/auth/social/naver/callback`

### 7-2. 프론트 콜백 주소와 provider 콜백 주소 구분

- 네이버/구글/카카오/깃허브 콘솔에 등록하는 주소는 백엔드 callback URL
  - 예: `http://127.0.0.1:8000/api/auth/social/naver/callback`
- `.env`의 `SOCIAL_LOGIN_REDIRECT_URL`은 프론트 콜백 페이지 주소
  - 예: `http://localhost:5173/auth/social/callback`

### 7-3. 소셜 로그인 중복 데이터 오류 처리

- 초기 구현 시 소셜 계정 연결 중 중복 데이터 오류 발생
- 계정 연결 로직 보강
  - 기존 provider identity 존재 여부 확인
  - 동일 사용자에 이미 같은 provider가 연결된 경우 재삽입 방지
  - 오류 발생 시 프론트 콜백 페이지로 에러 메시지 전달

### 7-4. DB 체크 제약 오류 해결

- 네이버 로그인 시 아래 오류 확인
  - `auth_identities_provider_check` 제약 위반
- 원인
  - DB 스키마가 `LOCAL`, `GOOGLE`, `GITHUB`만 허용
  - `NAVER`, `KAKAO` provider 값 미허용
- 해결
  - Alembic 마이그레이션 추가
  - `schema_v1.sql` 업데이트
  - 허용 provider 목록 확장
    - `LOCAL`
    - `GOOGLE`
    - `GITHUB`
    - `NAVER`
    - `KAKAO`

### 7-5. 프론트 콜백 페이지 접속 실패 확인

- 로그인 성공 후 아래 형태의 URL까지 도달
  - `http://127.0.0.1:5173/auth/social/callback#payload=...`
- 이후 브라우저에서 `ERR_CONNECTION_REFUSED` 발생 가능성 확인
- 원인
  - 프론트 dev 서버가 `127.0.0.1:5173`에서 수신하지 않거나 꺼져 있는 상태
- 대응
  - `SOCIAL_LOGIN_REDIRECT_URL`을 `localhost:5173` 기준으로 조정
  - 프론트 dev 서버 실제 바인딩 주소와 일치시키도록 설정 정리

### 7-6. 깃허브 사용자 이름 처리 방식

- GitHub는 사용자 `name` 값이 비어 있는 경우가 있음
- 처리 우선순위
  - `name`
  - `login`
  - 이메일 앞부분
- 이메일이 `/user` 응답에 없을 경우 `/user/emails` API 추가 조회

### 7-7. 자동가입 전 확인 모달 도입

- 일반적인 소셜 로그인 UX는 자동가입 후 바로 로그인
- 다만 서비스 정책상 자동가입 전에 한 번 더 사용자 의사를 묻는 흐름 필요
- 이에 따라 회원가입 페이지 이동 방식 대신 확인 모달 방식으로 변경
  - `아니요, 돌아가기`
  - `네, 계속 진행`

## 8. 검증 결과

- 백엔드 소셜 로그인 시작 URL 생성 정상 확인
- 네이버 OAuth 인증 후 backend callback 진입 확인
- 네이버 OAuth 성공 시 프론트 callback URL에 `#payload=` 전달 확인
- DB 제약 원인 파악 및 수정 완료
- 소셜 로그인 관련 예외 메시지 전달 로직 추가 완료
- 자동가입 확인 모달 흐름 구현 완료
- 깃허브 OAuth 연동 코드 반영 완료
- 백엔드 컴파일 체크 통과
- 프론트 빌드 통과

## 9. 현재 상태

- `네이버 / 구글 / 카카오 / 깃허브` 소셜 로그인 코드 반영 완료
- 네이버 OAuth 인증 및 payload 전달 성공 확인
- 깃허브 OAuth 연동 코드 반영 완료
- 미등록 소셜 계정은 자동가입 전 확인 모달 표시
- 사용자가 승인하면 자동가입 후 바로 로그인 진행

## 10. 실행 및 반영 시 필요 작업

### 백엔드

- Alembic 마이그레이션 적용

```powershell
alembic upgrade head
```

- 서버 실행

```powershell
uvicorn app.main:app --reload
```

### 프론트엔드

- 서버 실행

```powershell
npm run dev
```

## 11. 향후 작업 후보

- 운영 도메인 기준 Redirect URI 추가
- provider별 사용자 정보 동의항목 정교화
- 프론트 dev 서버의 `127.0.0.1` / `localhost` 바인딩 정책 명확화
- 소셜 계정 연동 해제 및 계정 병합 정책 정의
