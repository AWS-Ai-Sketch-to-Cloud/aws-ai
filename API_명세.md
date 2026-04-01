# API 명세

버전:
- `contract_version`: `v2`

기준:
- `users.login_id`를 로그인 식별자로 사용
- `projects.owner_id`는 인증 연동 전까지 nullable 허용
- `sessions`는 입력/상태/에러 중심 테이블
- `session_architectures`, `session_terraform_results`, `session_cost_results`는 `sessions.id` 기준 1:1 결과 테이블

공통 상태값:
- `CREATED`
- `ANALYZING`
- `ANALYZED`
- `GENERATING_TERRAFORM`
- `GENERATED`
- `COST_CALCULATED`
- `FAILED`

공통 에러코드:
- `PARSE_ERROR`
- `SCHEMA_ERROR`
- `TIMEOUT_ERROR`
- `INTERNAL_ERROR`
- `UNAUTHORIZED`
- `FORBIDDEN`

## 최종 API 목록

### 인증

| Method | Path | 설명 |
| --- | --- | --- |
| `POST` | `/api/auth/register` | 새 사용자 계정을 만들고 로컬 로그인 정보를 등록한다. |
| `POST` | `/api/auth/login` | `loginId`와 비밀번호로 로그인하고 인증 토큰을 발급한다. |
| `POST` | `/api/auth/logout` | 현재 로그인 세션을 종료하고 refresh token을 무효화한다. |
| `GET` | `/api/users/me` | 현재 로그인한 사용자의 기본 프로필 정보를 조회한다. |

### 업로드

| Method | Path | 설명 |
| --- | --- | --- |
| `POST` | `/api/uploads/images` | 스케치 이미지를 업로드하고 세션에서 사용할 URL을 발급한다. |

### 프로젝트

| Method | Path | 설명 |
| --- | --- | --- |
| `POST` | `/api/projects` | 새 프로젝트를 생성한다. |
| `GET` | `/api/projects` | 프로젝트 목록을 조회한다. |

### 세션

| Method | Path | 설명 |
| --- | --- | --- |
| `POST` | `/api/projects/{projectId}/sessions` | 특정 프로젝트 아래에 새 작업 세션을 생성한다. |
| `GET` | `/api/projects/{projectId}/sessions` | 특정 프로젝트의 세션 목록과 상태를 조회한다. |
| `GET` | `/api/sessions/{sessionId}` | 세션의 입력, 상태, 아키텍처, Terraform, 비용 결과를 한 번에 조회한다. |
| `POST` | `/api/sessions/{sessionId}/analyze` | 텍스트/스케치 입력을 분석해 세션의 아키텍처 JSON 결과를 생성한다. |
| `PATCH` | `/api/sessions/{sessionId}/status` | 세션 상태와 오류 정보를 갱신한다. |

### 결과 생성/저장

| Method | Path | 설명 |
| --- | --- | --- |
| `POST` | `/api/sessions/{sessionId}/architecture` | 세션의 아키텍처 JSON 결과를 저장한다. |
| `POST` | `/api/sessions/{sessionId}/terraform` | 저장된 아키텍처를 바탕으로 Terraform 결과를 생성하고 저장한다. |
| `POST` | `/api/sessions/{sessionId}/cost` | 저장된 아키텍처를 바탕으로 예상 비용을 계산하고 저장한다. |

## 1. 인증

### `POST /api/auth/register`

설명:
- 로컬 `loginId`/비밀번호 기반 회원가입
- `users`, `auth_identities` 동시 생성
- 새 사용자 계정을 만들고 로컬 로그인 정보를 함께 등록한다.

요청:

```json
{
  "loginId": "honggildong",
  "email": "user@example.com",
  "password": "plain-password",
  "displayName": "홍길동"
}
```

응답:

```json
{
  "userId": "uuid",
  "loginId": "honggildong",
  "email": "user@example.com",
  "displayName": "홍길동",
  "isActive": true,
  "role": "USER",
  "contractVersion": "v2"
}
```

비고:
- `auth_identities.provider`는 `LOCAL`
- `auth_identities.provider_user_id`는 `loginId`

### `POST /api/auth/login`

설명:
- `loginId`로 로그인
- 성공 시 access token 발급, `auth_sessions`에 refresh token 해시 저장
- `loginId`와 비밀번호로 로그인하고 인증 토큰을 발급한다.

요청:

```json
{
  "loginId": "honggildong",
  "password": "plain-password"
}
```

응답:

```json
{
  "user": {
    "userId": "uuid",
    "loginId": "honggildong",
    "email": "user@example.com",
    "displayName": "홍길동",
    "role": "USER"
  },
  "accessToken": "jwt-access-token",
  "refreshToken": "refresh-token",
  "contractVersion": "v2"
}
```

### `POST /api/auth/logout`

설명:
- 현재 로그인 세션 무효화
- `auth_sessions.revoked_at` 기록
- 현재 로그인 세션을 종료하고 refresh token을 무효화한다.

요청:

```json
{
  "refreshToken": "refresh-token"
}
```

응답:

```json
{
  "success": true,
  "contractVersion": "v2"
}
```

### `GET /api/users/me`

설명:
- 현재 로그인 사용자 기본 정보 조회
- 현재 로그인한 사용자의 기본 프로필 정보를 조회한다.

응답:

```json
{
  "userId": "uuid",
  "loginId": "honggildong",
  "email": "user@example.com",
  "displayName": "홍길동",
  "isActive": true,
  "role": "USER",
  "lastLoginAt": "2026-03-23T09:00:00Z",
  "contractVersion": "v2"
}
```

## 2. 프로젝트

### `POST /api/projects`

- 새 프로젝트를 생성한다.

요청:

```json
{
  "name": "쇼핑몰 인프라 설계",
  "description": "EC2 2대와 RDS 포함"
}
```

응답:

```json
{
  "projectId": "uuid",
  "name": "쇼핑몰 인프라 설계"
}
```

비고:
- 인증 전까지 `ownerId`를 응답 필수 필드로 강제하지 않음

### `GET /api/projects`

- 프로젝트 목록을 조회한다.

응답:

```json
[
  {
    "projectId": "uuid",
    "name": "쇼핑몰 인프라 설계",
    "description": "EC2 2대와 RDS 포함"
  }
]
```

## 3. 세션

### `POST /api/uploads/images`

설명:
- 스케치 이미지를 업로드하고 세션에서 사용할 URL을 발급한다.
- 업로드된 파일은 스토리지에 저장하고, API는 접근 가능한 URL 또는 파일 키를 반환한다.

요청:

```json
{
  "contentType": "image/png",
  "fileName": "architecture-sketch.png"
}
```

응답:

```json
{
  "fileId": "uuid",
  "url": "https://storage.example.com/uploads/architecture-sketch.png",
  "contentType": "image/png",
  "contractVersion": "v2"
}
```

비고:
- 실제 구현은 `multipart/form-data` 직접 업로드 또는 presigned URL 발급 방식 중 하나를 선택할 수 있다.
- 세션 생성 API의 `inputImageUrl`에는 이 API가 반환한 `url`을 넣는다.

### `POST /api/projects/{projectId}/sessions`

- 특정 프로젝트 아래에 새 작업 세션을 생성한다.

요청:

```json
{
  "inputType": "TEXT",
  "inputText": "EC2 2개와 MySQL RDS 1개를 프라이빗하게 구성",
  "inputImageUrl": null
}
```

스케치 입력 예시:

```json
{
  "inputType": "SKETCH",
  "inputText": null,
  "inputImageUrl": "https://storage.example.com/uploads/architecture-sketch.png"
}
```

응답:

```json
{
  "sessionId": "uuid",
  "versionNo": 1,
  "status": "CREATED"
}
```

### `GET /api/projects/{projectId}/sessions`

- 특정 프로젝트의 세션 목록과 상태를 조회한다.

응답:

```json
[
  {
    "sessionId": "uuid",
    "versionNo": 1,
    "status": "COST_CALCULATED",
    "createdAt": "2026-03-23T07:21:14Z"
  }
]
```

### `GET /api/sessions/{sessionId}`

- 세션의 입력, 상태, 아키텍처, Terraform, 비용 결과를 한 번에 조회한다.

응답:

```json
{
  "sessionId": "uuid",
  "projectId": "uuid",
  "versionNo": 1,
  "inputType": "TEXT",
  "inputText": "EC2 2개와 MySQL RDS 1개를 프라이빗하게 구성",
  "status": "COST_CALCULATED",
  "architecture": {
    "schemaVersion": "v1",
    "architectureJson": {
      "vpc": true,
      "ec2": {
        "count": 2,
        "instance_type": "t3.micro"
      },
      "rds": {
        "enabled": true,
        "engine": "mysql"
      },
      "public": false,
      "region": "ap-northeast-2"
    }
  },
  "terraform": {
    "validationStatus": "PASSED",
    "terraformCode": "resource ...",
    "validationOutput": ""
  },
  "cost": {
    "currency": "KRW",
    "region": "ap-northeast-2",
    "monthlyTotal": 30000,
    "costBreakdownJson": {
      "ec2": 12000,
      "rds": 18000,
      "total": 30000
    },
    "assumptionJson": {
      "currency": "KRW",
      "region": "ap-northeast-2",
      "ec2_type": "t3.micro",
      "ec2_count": 2,
      "rds_enabled": true,
      "rds_engine": "mysql",
      "hours_per_month": 730,
      "pricing_version": "v1-static"
    }
  },
  "error": null
}
```

### `PATCH /api/sessions/{sessionId}/status`

- 세션 상태와 오류 정보를 갱신한다.

요청:

```json
{
  "status": "FAILED",
  "errorCode": "SCHEMA_ERROR",
  "errorMessage": "missing required field: ec2.count"
}
```

비고:
- 내부 서비스 로직용으로만 유지해도 됨

### `POST /api/sessions/{sessionId}/analyze`

- 텍스트 또는 스케치 입력을 분석해 세션의 아키텍처 JSON 결과를 생성한다.
- 생성 성공 시 세션 상태는 `ANALYZED`가 된다.
- 이 엔드포인트는 프론트의 공식 분석 시작 경로다.

요청:

```json
{
  "input_text": "EC2 2개와 MySQL RDS 1개를 프라이빗하게 구성",
  "input_type": "text",
  "input_image_data_url": null
}
```

스케치 입력 예시:

```json
{
  "input_text": "Analyze the uploaded architecture diagram and infer AWS resources and counts precisely.",
  "input_type": "sketch",
  "input_image_data_url": "data:image/png;base64,..."
}
```

응답:

```json
{
  "session_id": "uuid",
  "status": "generated",
  "parsed_json": {
    "vpc": true,
    "ec2": {
      "count": 2,
      "instance_type": "t3.micro"
    },
    "rds": {
      "enabled": true,
      "engine": "mysql"
    },
    "public": false,
    "region": "ap-northeast-2"
  },
  "analysisMeta": {
    "provider": "bedrock",
    "modelId": "model-id",
    "usedImage": false,
    "fallbackUsed": false
  },
  "contract_version": "v2"
}
```

비고:
- 레거시 `/sessions/...` 계열 엔드포인트는 정리되었으며, 분석 시작 경로는 `/api/sessions/{sessionId}/analyze`만 사용한다.

## 4. 결과 저장/생성

### `POST /api/sessions/{sessionId}/architecture`

- 세션의 아키텍처 JSON 결과를 저장한다.

요청:

```json
{
  "schemaVersion": "v1",
  "architectureJson": {
    "vpc": true,
    "ec2": {
      "count": 2,
      "instance_type": "t3.micro"
    },
    "rds": {
      "enabled": true,
      "engine": "mysql"
    },
    "public": false,
    "region": "ap-northeast-2"
  }
}
```

응답:

```json
{
  "sessionId": "uuid",
  "status": "ANALYZED"
}
```

### `POST /api/sessions/{sessionId}/terraform`

- 저장된 아키텍처를 바탕으로 Terraform 결과를 생성하고 저장한다.

응답:

```json
{
  "sessionId": "uuid",
  "status": "GENERATED",
  "validationStatus": "PASSED",
  "terraformCode": "resource ...",
  "validationOutput": "",
  "contractVersion": "v2"
}
```

### `POST /api/sessions/{sessionId}/cost`

- 저장된 아키텍처를 바탕으로 예상 비용을 계산하고 저장한다.

응답:

```json
{
  "sessionId": "uuid",
  "status": "COST_CALCULATED",
  "currency": "KRW",
  "region": "ap-northeast-2",
  "monthlyTotal": 30000,
  "costBreakdownJson": {
    "ec2": 12000,
    "rds": 18000,
    "total": 30000
  },
  "assumptionJson": {
    "currency": "KRW",
    "region": "ap-northeast-2",
    "ec2_type": "t3.micro",
    "ec2_count": 2,
    "rds_enabled": true,
    "rds_engine": "mysql",
    "hours_per_month": 730,
    "pricing_version": "v1-static"
  },
  "contractVersion": "v2"
}
```
