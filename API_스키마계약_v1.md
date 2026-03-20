# API/스키마 계약 v2

목적:
- 서비스 파이프라인 초안의 DB 명세를 기준으로 FastAPI 백엔드와 React / vite 프론트엔드가 같은 계약으로 개발한다.
- 인증, 프로젝트, 세션, 결과 저장 API의 필드와 상태값을 고정해 구현 흔들림을 줄인다.

버전:
- `contract_version`: `v2`
- 변경 원칙: breaking change 발생 시 다음 버전으로 올린다.

## 1. 공통 상태값

- `CREATED`: 세션 생성 완료
- `ANALYZING`: 입력 해석 진행 중
- `ANALYZED`: 아키텍처 JSON 저장 완료
- `GENERATING_TERRAFORM`: Terraform 생성 진행 중
- `GENERATED`: Terraform 코드 저장 완료
- `COST_CALCULATED`: 비용 계산 저장 완료
- `FAILED`: 처리 실패

## 2. 공통 에러코드

- `PARSE_ERROR`: LLM 응답 JSON 파싱 실패
- `SCHEMA_ERROR`: JSON 스키마 검증 실패
- `TERRAFORM_GENERATION_ERROR`: Terraform 생성 실패
- `VALIDATION_ERROR`: Terraform validate 실패
- `COST_CALCULATION_ERROR`: 비용 계산 실패
- `TIMEOUT_ERROR`: 외부 호출 타임아웃
- `UNAUTHORIZED`: 인증 실패
- `FORBIDDEN`: 권한 부족
- `INTERNAL_ERROR`: 기타 서버 오류

## 3. 인증/계정 계약

### 3-1) `POST /api/auth/register`

설명:
- 로컬 이메일/비밀번호 기반 회원가입
- `users`, `auth_identities`를 함께 생성

요청 예시:

```json
{
  "email": "user@example.com",
  "password": "plain-password",
  "displayName": "홍길동"
}
```

응답 예시:

```json
{
  "userId": "uuid",
  "email": "user@example.com",
  "displayName": "홍길동",
  "isActive": true,
  "role": "USER",
  "contractVersion": "v2"
}
```

### 3-2) `POST /api/auth/login`

설명:
- 로컬 로그인 성공 시 access token 발급, `auth_sessions`에 refresh token 해시 저장

요청 예시:

```json
{
  "email": "user@example.com",
  "password": "plain-password"
}
```

응답 예시:

```json
{
  "user": {
    "userId": "uuid",
    "email": "user@example.com",
    "displayName": "홍길동",
    "role": "USER"
  },
  "accessToken": "jwt-access-token",
  "refreshToken": "refresh-token",
  "contractVersion": "v2"
}
```

### 3-3) `POST /api/auth/logout`

설명:
- 현재 로그인 세션을 무효화하고 `auth_sessions.revoked_at`을 기록

요청 예시:

```json
{
  "refreshToken": "refresh-token"
}
```

응답 예시:

```json
{
  "success": true,
  "contractVersion": "v2"
}
```

## 4. 프로젝트/세션 계약

### 4-1) `POST /api/projects`

설명:
- 로그인한 사용자의 새 프로젝트 생성
- DB 기준: `projects.owner_id = auth user id`

요청 예시:

```json
{
  "name": "쇼핑몰 인프라 설계",
  "description": "EC2 2대와 RDS 포함"
}
```

응답 예시:

```json
{
  "projectId": "uuid",
  "name": "쇼핑몰 인프라 설계",
  "description": "EC2 2대와 RDS 포함",
  "ownerId": "uuid",
  "createdAt": "2026-03-20T10:00:00Z",
  "contractVersion": "v2"
}
```

### 4-2) `GET /api/projects`

설명:
- 로그인한 사용자의 프로젝트 목록 조회

응답 예시:

```json
{
  "items": [
    {
      "projectId": "uuid",
      "name": "쇼핑몰 인프라 설계",
      "description": "EC2 2대와 RDS 포함",
      "createdAt": "2026-03-20T10:00:00Z",
      "updatedAt": "2026-03-20T10:00:00Z"
    }
  ],
  "contractVersion": "v2"
}
```

### 4-3) `POST /api/projects/{projectId}/sessions`

설명:
- 프로젝트 하위에 새 세션 생성
- DB 기준: `sessions.version_no`는 프로젝트 내에서 1씩 증가

요청 예시:

```json
{
  "inputType": "TEXT",
  "inputText": "EC2 2개와 MySQL RDS 1개를 퍼블릭하게 구성",
  "inputImageUrl": null
}
```

응답 예시:

```json
{
  "sessionId": "uuid",
  "projectId": "uuid",
  "versionNo": 1,
  "status": "CREATED",
  "createdAt": "2026-03-20T10:00:00Z",
  "contractVersion": "v2"
}
```

### 4-4) `GET /api/projects/{projectId}/sessions`

설명:
- 프로젝트별 세션 목록 조회
- 최소 응답 필드: `versionNo`, `status`, `createdAt`

응답 예시:

```json
{
  "items": [
    {
      "sessionId": "uuid",
      "versionNo": 1,
      "inputType": "TEXT",
      "status": "CREATED",
      "createdAt": "2026-03-20T10:00:00Z",
      "updatedAt": "2026-03-20T10:00:00Z"
    }
  ],
  "contractVersion": "v2"
}
```

### 4-5) `GET /api/sessions/{sessionId}`

설명:
- 세션 상세 단건 조회
- `sessions`, `session_architectures`, `session_terraform_results`, `session_cost_results`를 조합한 응답

응답 예시:

```json
{
  "sessionId": "uuid",
  "projectId": "uuid",
  "versionNo": 1,
  "inputType": "TEXT",
  "inputText": "EC2 2개와 MySQL RDS 1개를 퍼블릭하게 구성",
  "inputImageUrl": null,
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
      "public": true,
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
    "assumptionJson": {
      "ec2Type": "t3.micro",
      "rdsType": "db.t3.micro",
      "hoursPerMonth": 730
    },
    "monthlyTotal": 30000,
    "costBreakdownJson": {
      "ec2": 12000,
      "rds": 18000
    }
  },
  "error": null,
  "createdAt": "2026-03-20T10:00:00Z",
  "updatedAt": "2026-03-20T10:05:00Z",
  "contractVersion": "v2"
}
```

## 5. 결과 저장 계약

### 5-1) `POST /api/sessions/{sessionId}/architecture`

설명:
- `session_architectures` 저장
- 성공 저장 이후 세션 상태는 최소 `ANALYZED`까지 반영 가능해야 한다.

요청 예시:

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
    "public": true,
    "region": "ap-northeast-2"
  }
}
```

응답 예시:

```json
{
  "sessionId": "uuid",
  "status": "ANALYZED",
  "contractVersion": "v2"
}
```

### 5-2) `POST /api/sessions/{sessionId}/terraform`

설명:
- `session_terraform_results` 저장
- 성공 저장 이후 세션 상태는 최소 `GENERATED`까지 반영 가능해야 한다.

요청 예시:

```json
{
  "terraformCode": "resource ...",
  "validationStatus": "PASSED",
  "validationOutput": ""
}
```

응답 예시:

```json
{
  "sessionId": "uuid",
  "status": "GENERATED",
  "contractVersion": "v2"
}
```

### 5-3) `POST /api/sessions/{sessionId}/cost`

설명:
- `session_cost_results` 저장
- 성공 저장 이후 세션 상태는 `COST_CALCULATED`까지 반영 가능해야 한다.

요청 예시:

```json
{
  "currency": "KRW",
  "region": "ap-northeast-2",
  "assumptionJson": {
    "ec2Type": "t3.micro",
    "rdsType": "db.t3.micro",
    "hoursPerMonth": 730
  },
  "monthlyTotal": 30000,
  "costBreakdownJson": {
    "ec2": 12000,
    "rds": 18000
  }
}
```

응답 예시:

```json
{
  "sessionId": "uuid",
  "status": "COST_CALCULATED",
  "contractVersion": "v2"
}
```

### 5-4) `PATCH /api/sessions/{sessionId}/status`

설명:
- 세션 상태와 실패 정보를 업데이트
- 외부 공개 API보다 내부 서비스 처리용에 가깝다.

요청 예시:

```json
{
  "status": "FAILED",
  "errorCode": "SCHEMA_ERROR",
  "errorMessage": "missing required field: ec2.count"
}
```

응답 예시:

```json
{
  "sessionId": "uuid",
  "status": "FAILED",
  "contractVersion": "v2"
}
```

## 6. A -> B 데이터 인계 규칙

- A는 `architectureJson`을 [A_JSON_스키마_v1.json](/c:/workspace/side-Project/aws-ai/A_JSON_스키마_v1.json) 검증 통과한 값만 전달한다.
- B는 `architectureJson` 원본(JSON)을 `session_architectures.architecture_json`에 저장한다.
- B는 Terraform 결과를 `session_terraform_results`에 저장하고 `validation_status`를 함께 저장한다.
- B는 비용 결과를 `session_cost_results`에 저장하고 `assumption_json`을 함께 저장한다.
- B는 실패 시 `sessions.error_code`, `sessions.error_message`를 저장하고 `status=FAILED`로 업데이트한다.

## 7. DB 매핑 규칙

- `users.email`은 UNIQUE 여야 한다.
- `projects.owner_id`는 `users.id`를 참조한다.
- `sessions.project_id`는 `projects.id`를 참조한다.
- `session_architectures.session_id`, `session_terraform_results.session_id`, `session_cost_results.session_id`는 각각 `sessions.id`와 1:1 관계다.
- `sessions.version_no`는 같은 프로젝트 내에서 UNIQUE 여야 한다.

## 8. 기본값 규칙

- `users.is_active` 기본값: `true`
- `users.role` 기본값: `USER`
- `inputType` 기본값: `TEXT`
- `schemaVersion` 기본값: `v1`
- `currency` 기본값: `KRW`
- `region` 미지정 시 기본값: `ap-northeast-2`
- `ec2.instance_type` 미지정 시 기본값: `t3.micro`
- 공개 여부 불명확 시 기본값: `public=false`
- DB 불명확 시 기본값: `rds.enabled=false`, `rds.engine=null`
