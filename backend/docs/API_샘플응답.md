# API 샘플 응답 (v2)

기준:
- Base URL: `http://127.0.0.1:8000`
- 계약 버전: `contractVersion = "v2"`

## 1) 회원가입

`POST /api/auth/register`

```json
{
  "userId": "5d54e822-6448-49f2-94ff-d5f743ae4c85",
  "loginId": "honggildong",
  "email": "user@example.com",
  "displayName": "홍길동",
  "isActive": true,
  "role": "USER",
  "contractVersion": "v2"
}
```

## 2) 로그인

`POST /api/auth/login`

```json
{
  "user": {
    "userId": "5d54e822-6448-49f2-94ff-d5f743ae4c85",
    "loginId": "honggildong",
    "email": "user@example.com",
    "displayName": "홍길동",
    "role": "USER"
  },
  "accessToken": "uid:5d54e822-6448-49f2-94ff-d5f743ae4c85",
  "refreshToken": "random-token",
  "contractVersion": "v2"
}
```

## 3) 내 정보 조회

`GET /api/users/me`

```json
{
  "userId": "5d54e822-6448-49f2-94ff-d5f743ae4c85",
  "loginId": "honggildong",
  "email": "user@example.com",
  "displayName": "홍길동",
  "isActive": true,
  "role": "USER",
  "lastLoginAt": "2026-03-23T09:00:00Z",
  "contractVersion": "v2"
}
```

## 4) 이미지 업로드 URL 발급

`POST /api/uploads/images`

```json
{
  "fileId": "af8d45b2-4efd-4f80-bceb-b9dbf5e2b33a",
  "url": "https://storage.example.com/uploads/af8d45b2-4efd-4f80-bceb-b9dbf5e2b33a/architecture-sketch.png",
  "contentType": "image/png",
  "contractVersion": "v2"
}
```

## 5) 세션 생성

`POST /api/projects/{projectId}/sessions`

```json
{
  "sessionId": "ce8b3fd4-aac0-4d9c-a886-8adf163cb1f5",
  "projectId": "ce8b3fd4-aac0-4d9c-a886-8adf163cb1f4",
  "versionNo": 1,
  "status": "CREATED",
  "createdAt": "2026-03-23T09:00:00Z",
  "contractVersion": "v2"
}
```

## 6) 상태 갱신

`PATCH /api/sessions/{sessionId}/status`

```json
{
  "sessionId": "ce8b3fd4-aac0-4d9c-a886-8adf163cb1f5",
  "status": "ANALYZING",
  "contractVersion": "v2"
}
```

## 7) Terraform 생성

`POST /api/sessions/{sessionId}/terraform`

```json
{
  "sessionId": "ce8b3fd4-aac0-4d9c-a886-8adf163cb1f5",
  "status": "GENERATED",
  "validationStatus": "PASSED",
  "terraformCode": "resource ...",
  "validationOutput": "",
  "contractVersion": "v2"
}
```

## 8) 비용 계산

`POST /api/sessions/{sessionId}/cost`

```json
{
  "sessionId": "ce8b3fd4-aac0-4d9c-a886-8adf163cb1f5",
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
