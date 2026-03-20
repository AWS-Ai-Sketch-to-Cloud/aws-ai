# API/스키마 계약 v1

목적:
- A(생성 파이프라인)와 B(서비스 파이프라인)가 같은 데이터 계약으로 개발
- MVP 범위(`VPC`, `EC2`, `RDS`)에서 API/DB/프론트 간 필드 흔들림 방지

버전:
- `contract_version`: `v1`
- 변경 원칙: breaking change 발생 시 `v2`로 올림

## 1. 공통 상태값

- `created`: 세션 생성 완료
- `analyzing`: AI 해석 진행 중
- `generated`: JSON 생성 및 검증 성공
- `failed`: 파싱/검증/타임아웃 실패

## 2. 공통 에러코드

- `PARSE_ERROR`: LLM 응답 JSON 파싱 실패
- `SCHEMA_ERROR`: JSON 스키마 검증 실패
- `TIMEOUT_ERROR`: LLM 호출 타임아웃
- `INTERNAL_ERROR`: 기타 서버 오류

## 3. 엔드포인트 계약

### 3-1) `POST /sessions`

요청 스키마:
- [contracts/session_create.request.schema.json](c:\Users\junse\Desktop\vscode\team-project\aws-ai\contracts\session_create.request.schema.json)

응답(성공):
```json
{
  "session_id": "ses_20260320_0001",
  "project_id": "proj_demo",
  "status": "created",
  "created_at": "2026-03-20T10:00:00Z",
  "contract_version": "v1"
}
```

### 3-2) `POST /sessions/{session_id}/analyze`

요청 스키마:
- [contracts/analyze.request.schema.json](c:\Users\junse\Desktop\vscode\team-project\aws-ai\contracts\analyze.request.schema.json)

성공 응답:
```json
{
  "session_id": "ses_20260320_0001",
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
    "public": true,
    "region": "ap-northeast-2"
  },
  "contract_version": "v1"
}
```

실패 응답:
```json
{
  "session_id": "ses_20260320_0001",
  "status": "failed",
  "error": {
    "code": "SCHEMA_ERROR",
    "message": "missing required field: ec2.count"
  },
  "contract_version": "v1"
}
```

### 3-3) `GET /sessions/{session_id}`

응답 스키마:
- [contracts/session.response.schema.json](c:\Users\junse\Desktop\vscode\team-project\aws-ai\contracts\session.response.schema.json)

응답 예시:
```json
{
  "session_id": "ses_20260320_0001",
  "project_id": "proj_demo",
  "status": "generated",
  "input_text": "서울 리전에 EC2 2개와 mysql rds 1개",
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
  "error": null,
  "created_at": "2026-03-20T10:00:00Z",
  "updated_at": "2026-03-20T10:00:12Z",
  "contract_version": "v1"
}
```

## 4. A -> B 데이터 인계 규칙

- A는 `parsed_json`를 [A_JSON_스키마_v1.json](c:\Users\junse\Desktop\vscode\team-project\aws-ai\A_JSON_스키마_v1.json) 검증 통과한 값만 전달
- B는 `parsed_json` 원본(JSON) 그대로 저장
- B는 실패 시 `error.code`, `error.message`를 저장하고 `status=failed`로 업데이트

## 5. 기본값 규칙 (A 책임)

- `region` 미지정: `ap-northeast-2`
- `ec2.instance_type` 미지정: `t3.micro`
- 공개 여부 불명확: `public=false`
- DB 불명확: `rds.enabled=false`, `rds.engine=null`

