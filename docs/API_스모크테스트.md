# API 스모크 테스트 (v1)

목적:
- 팀원이 같은 순서로 백엔드 파이프라인 동작을 빠르게 확인
- 흐름: `project -> session -> analyze -> terraform -> cost -> detail`

전제:
- 서버 실행: `uvicorn app.main:app --reload`
- `BEDROCK_ENABLED=false` 권장(비용 0)
- 기본 주소: `http://127.0.0.1:8000`

## 1) 프로젝트 생성

```bash
curl -X POST http://127.0.0.1:8000/api/projects \
  -H "Content-Type: application/json" \
  -d "{\"name\":\"smoke-project\",\"description\":\"pipeline smoke\"}"
```

응답에서 `projectId` 저장.

## 2) 세션 생성

```bash
curl -X POST http://127.0.0.1:8000/api/projects/{projectId}/sessions \
  -H "Content-Type: application/json" \
  -d "{\"inputType\":\"TEXT\",\"inputText\":\"서울 리전에 EC2 2개 mysql rds 퍼블릭\"}"
```

응답에서 `sessionId` 저장.

## 3) 분석 실행(JSON 생성)

```bash
curl -X POST http://127.0.0.1:8000/sessions/{sessionId}/analyze \
  -H "Content-Type: application/json" \
  -d "{\"input_text\":\"서울 리전에 EC2 2개 mysql rds 퍼블릭\"}"
```

기대: `status=generated`

## 4) Terraform 생성/검증

```bash
curl -X POST http://127.0.0.1:8000/api/sessions/{sessionId}/terraform
```

기대:
- `status=GENERATED`
- `validationStatus=PASSED` 또는 `FAILED`
- `FAILED`인데 메시지가 `terraform command not found`면 로컬 Terraform 설치 필요

## 5) 비용 계산

```bash
curl -X POST http://127.0.0.1:8000/api/sessions/{sessionId}/cost
```

기대: `status=COST_CALCULATED`, `monthlyTotal > 0`

## 6) 상세 조회

```bash
curl http://127.0.0.1:8000/api/sessions/{sessionId}
```

기대:
- `architecture` 존재
- `terraform` 존재
- `cost` 존재

## 7) 프로젝트 세션 목록 조회

```bash
curl http://127.0.0.1:8000/api/projects/{projectId}/sessions
```

기대: 방금 생성한 세션이 `status=COST_CALCULATED`로 표시

