# A 입력 테스트셋 v1 (20개)

목적:
- 사용자 입력을 JSON 스키마 v1으로 안정적으로 변환 가능한지 검증
- MVP 범위(`VPC`, `EC2`, `RDS`) 내에서 쉬운 케이스/애매한 케이스를 함께 테스트

규칙:
- `region`이 입력에 없으면 기본값 `ap-northeast-2`
- 인스턴스 타입이 없으면 기본값 `t3.micro`
- 입력 문장에 "공개/퍼블릭/인터넷" 맥락이 없으면 `public=false`
- RDS 엔진이 불명확하면 `rds.enabled=false`, `rds.engine=null`

## 테스트 케이스

1.
- type: text
- input: `서울 리전에 EC2 1개만 만들어줘`
- expected:
```json
{"vpc":true,"ec2":{"count":1,"instance_type":"t3.micro"},"rds":{"enabled":false,"engine":null},"public":false,"region":"ap-northeast-2"}
```

2.
- type: text
- input: `EC2 2개랑 MySQL RDS 1개 필요해`
- expected:
```json
{"vpc":true,"ec2":{"count":2,"instance_type":"t3.micro"},"rds":{"enabled":true,"engine":"mysql"},"public":false,"region":"ap-northeast-2"}
```

3.
- type: text
- input: `퍼블릭 웹서버 EC2 두 대 배치하고 DB는 postgres로 붙여줘`
- expected:
```json
{"vpc":true,"ec2":{"count":2,"instance_type":"t3.micro"},"rds":{"enabled":true,"engine":"postgres"},"public":true,"region":"ap-northeast-2"}
```

4.
- type: text
- input: `도쿄 리전에 EC2 3개, DB는 필요 없음`
- expected:
```json
{"vpc":true,"ec2":{"count":3,"instance_type":"t3.micro"},"rds":{"enabled":false,"engine":null},"public":false,"region":"ap-northeast-1"}
```

5.
- type: text
- input: `버지니아 북부에 t3.small EC2 2개랑 mysql rds`
- expected:
```json
{"vpc":true,"ec2":{"count":2,"instance_type":"t3.small"},"rds":{"enabled":true,"engine":"mysql"},"public":false,"region":"us-east-1"}
```

6.
- type: text
- input: `EC2 1개, RDS postgres 1개, 외부 공개 안함`
- expected:
```json
{"vpc":true,"ec2":{"count":1,"instance_type":"t3.micro"},"rds":{"enabled":true,"engine":"postgres"},"public":false,"region":"ap-northeast-2"}
```

7.
- type: text
- input: `인터넷에서 접속 가능한 웹 서버 1대와 mysql 데이터베이스`
- expected:
```json
{"vpc":true,"ec2":{"count":1,"instance_type":"t3.micro"},"rds":{"enabled":true,"engine":"mysql"},"public":true,"region":"ap-northeast-2"}
```

8.
- type: text
- input: `RDS는 빼고 EC2만 4대`
- expected:
```json
{"vpc":true,"ec2":{"count":4,"instance_type":"t3.micro"},"rds":{"enabled":false,"engine":null},"public":false,"region":"ap-northeast-2"}
```

9.
- type: text
- input: `서울, private 환경, app 서버 2대 + postgres`
- expected:
```json
{"vpc":true,"ec2":{"count":2,"instance_type":"t3.micro"},"rds":{"enabled":true,"engine":"postgres"},"public":false,"region":"ap-northeast-2"}
```

10.
- type: text
- input: `오하이오 리전에 EC2 한 대 공개 배치`
- expected:
```json
{"vpc":true,"ec2":{"count":1,"instance_type":"t3.micro"},"rds":{"enabled":false,"engine":null},"public":true,"region":"us-east-2"}
```

11.
- type: text (ambiguous)
- input: `작게 시작하고 싶어. 서버 몇 개랑 DB도 필요할지도`
- expected:
```json
{"vpc":true,"ec2":{"count":1,"instance_type":"t3.micro"},"rds":{"enabled":false,"engine":null},"public":false,"region":"ap-northeast-2"}
```

12.
- type: text (ambiguous)
- input: `웹이랑 데이터 저장소 구성해줘`
- expected:
```json
{"vpc":true,"ec2":{"count":1,"instance_type":"t3.micro"},"rds":{"enabled":false,"engine":null},"public":false,"region":"ap-northeast-2"}
```

13.
- type: text (ambiguous)
- input: `가용성 고려해서 EC2 여러 대`
- expected:
```json
{"vpc":true,"ec2":{"count":2,"instance_type":"t3.micro"},"rds":{"enabled":false,"engine":null},"public":false,"region":"ap-northeast-2"}
```

14.
- type: text (ambiguous)
- input: `DB는 필요할 수 있는데 아직 미정`
- expected:
```json
{"vpc":true,"ec2":{"count":1,"instance_type":"t3.micro"},"rds":{"enabled":false,"engine":null},"public":false,"region":"ap-northeast-2"}
```

15.
- type: text (ambiguous)
- input: `퍼블릭으로 열어야 할지 모르겠어`
- expected:
```json
{"vpc":true,"ec2":{"count":1,"instance_type":"t3.micro"},"rds":{"enabled":false,"engine":null},"public":false,"region":"ap-northeast-2"}
```

16.
- type: sketch
- input: `스케치 설명: 인터넷 -> EC2 x2 -> RDS(mysql), 서울`
- expected:
```json
{"vpc":true,"ec2":{"count":2,"instance_type":"t3.micro"},"rds":{"enabled":true,"engine":"mysql"},"public":true,"region":"ap-northeast-2"}
```

17.
- type: sketch
- input: `스케치 설명: 내부망 EC2 x1, DB 없음`
- expected:
```json
{"vpc":true,"ec2":{"count":1,"instance_type":"t3.micro"},"rds":{"enabled":false,"engine":null},"public":false,"region":"ap-northeast-2"}
```

18.
- type: sketch
- input: `스케치 설명: 웹서버 3개, postgres DB 1개, 퍼블릭`
- expected:
```json
{"vpc":true,"ec2":{"count":3,"instance_type":"t3.micro"},"rds":{"enabled":true,"engine":"postgres"},"public":true,"region":"ap-northeast-2"}
```

19.
- type: text
- input: `싱가포르 리전에 t3.medium EC2 2개랑 postgres`
- expected:
```json
{"vpc":true,"ec2":{"count":2,"instance_type":"t3.medium"},"rds":{"enabled":true,"engine":"postgres"},"public":false,"region":"ap-southeast-1"}
```

20.
- type: text
- input: `서울에 EC2 2개, 인터넷 공개, DB는 mysql`
- expected:
```json
{"vpc":true,"ec2":{"count":2,"instance_type":"t3.micro"},"rds":{"enabled":true,"engine":"mysql"},"public":true,"region":"ap-northeast-2"}
```

