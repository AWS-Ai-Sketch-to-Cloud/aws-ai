# API 샘플 응답 (프론트 연동용)

기준:
- Base URL: `http://127.0.0.1:8000`
- DB 스키마 리비전: `01898398e88a`
- 개발 기본 모드: `BEDROCK_ENABLED=false`

## 1) 프로젝트 생성

`POST /api/projects`

요청:
```json
{
  "name": "smoke-project",
  "description": "pipeline smoke"
}
```

응답:
```json
{
  "projectId": "8b066ca0-bb6a-4f22-a769-1efead0a8d62",
  "name": "smoke-project"
}
```

## 2) 세션 생성

`POST /api/projects/{projectId}/sessions`

요청:
```json
{
  "inputType": "TEXT",
  "inputText": "서울 리전에 EC2 2개 mysql rds 퍼블릭"
}
```

응답:
```json
{
  "sessionId": "ce8b3fd4-aac0-4d9c-a886-8adf163cb1f5",
  "versionNo": 1,
  "status": "CREATED"
}
```

## 3) 분석 실행

`POST /sessions/{sessionId}/analyze`

요청:
```json
{
  "input_text": "서울 리전에 EC2 2개 mysql rds 퍼블릭"
}
```

응답:
```json
{
  "session_id": "ce8b3fd4-aac0-4d9c-a886-8adf163cb1f5",
  "status": "generated",
  "parsed_json": {
    "vpc": true,
    "ec2": { "count": 2, "instance_type": "t3.micro" },
    "rds": { "enabled": true, "engine": "mysql" },
    "public": false,
    "region": "ap-northeast-2"
  },
  "error": null,
  "contract_version": "v1"
}
```

## 4) Terraform 생성/검증

`POST /api/sessions/{sessionId}/terraform`

응답:
```json
{
  "sessionId": "ce8b3fd4-aac0-4d9c-a886-8adf163cb1f5",
  "status": "GENERATED",
  "validationStatus": "FAILED",
  "terraformCode": "terraform { ... }",
  "validationOutput": "terraform command not found. Install Terraform and ensure it is in PATH."
}
```

참고:
- Terraform CLI 설치 시 `validationStatus`가 `PASSED`로 바뀔 수 있음

## 5) 비용 계산

`POST /api/sessions/{sessionId}/cost`

응답:
```json
{
  "sessionId": "ce8b3fd4-aac0-4d9c-a886-8adf163cb1f5",
  "status": "COST_CALCULATED",
  "currency": "KRW",
  "region": "ap-northeast-2",
  "monthlyTotal": 42000.0,
  "costBreakdownJson": {
    "ec2": 24000,
    "rds": 18000,
    "total": 42000
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
}
```

## 6) 세션 상세 조회

`GET /api/sessions/{sessionId}`

응답:
```json
{
  "sessionId": "ce8b3fd4-aac0-4d9c-a886-8adf163cb1f5",
  "projectId": "8b066ca0-bb6a-4f22-a769-1efead0a8d62",
  "versionNo": 1,
  "inputType": "TEXT",
  "inputText": "서울 리전에 EC2 2개 mysql rds 퍼블릭",
  "status": "COST_CALCULATED",
  "architecture": {
    "schemaVersion": "v1",
    "architectureJson": {
      "vpc": true,
      "ec2": { "count": 2, "instance_type": "t3.micro" },
      "rds": { "enabled": true, "engine": "mysql" },
      "public": false,
      "region": "ap-northeast-2"
    }
  },
  "terraform": {
    "validationStatus": "FAILED",
    "terraformCode": "terraform { ... }",
    "validationOutput": "terraform command not found. Install Terraform and ensure it is in PATH."
  },
  "cost": {
    "currency": "KRW",
    "region": "ap-northeast-2",
    "monthlyTotal": 42000.0,
    "costBreakdownJson": {
      "ec2": 24000,
      "rds": 18000,
      "total": 42000
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

## 7) 프로젝트 세션 목록 조회

`GET /api/projects/{projectId}/sessions`

응답:
```json
[
  {
    "sessionId": "ce8b3fd4-aac0-4d9c-a886-8adf163cb1f5",
    "versionNo": 1,
    "status": "COST_CALCULATED",
    "createdAt": "2026-03-23T07:21:14Z"
  }
]
```

