# A 입력 테스트셋 v2 (추가 20개)

목적:
- v1(20개) 이후 케이스 다양성 확대
- 리전/인스턴스 타입/모호한 표현/혼합 문장 대응 점검

규칙:
- 기본값: `region=ap-northeast-2`, `instance_type=t3.micro`, `public=false`
- DB 불명확 시 `rds.enabled=false`, `rds.engine=null`

## 테스트 케이스

1.
- type: text
- input: `서울에서 EC2 5대 운영하고 DB는 mysql`
- expected:
```json
{"vpc":true,"ec2":{"count":5,"instance_type":"t3.micro"},"rds":{"enabled":true,"engine":"mysql"},"public":false,"region":"ap-northeast-2"}
```

2.
- type: text
- input: `도쿄 리전, t3.small EC2 2개, postgres, private`
- expected:
```json
{"vpc":true,"ec2":{"count":2,"instance_type":"t3.small"},"rds":{"enabled":true,"engine":"postgres"},"public":false,"region":"ap-northeast-1"}
```

3.
- type: text
- input: `us-east-1에 ec2 1 public`
- expected:
```json
{"vpc":true,"ec2":{"count":1,"instance_type":"t3.micro"},"rds":{"enabled":false,"engine":null},"public":true,"region":"us-east-1"}
```

4.
- type: text
- input: `싱가포르에 ec2 3대, db 없음`
- expected:
```json
{"vpc":true,"ec2":{"count":3,"instance_type":"t3.micro"},"rds":{"enabled":false,"engine":null},"public":false,"region":"ap-southeast-1"}
```

5.
- type: text
- input: `오하이오 region t3.medium ec2 2 mysql rds`
- expected:
```json
{"vpc":true,"ec2":{"count":2,"instance_type":"t3.medium"},"rds":{"enabled":true,"engine":"mysql"},"public":false,"region":"us-east-2"}
```

6.
- type: text
- input: `EC2 x3, postgres RDS, 인터넷 공개`
- expected:
```json
{"vpc":true,"ec2":{"count":3,"instance_type":"t3.micro"},"rds":{"enabled":true,"engine":"postgres"},"public":true,"region":"ap-northeast-2"}
```

7.
- type: text
- input: `서버 두 대, 데이터베이스는 mysql, 비공개`
- expected:
```json
{"vpc":true,"ec2":{"count":2,"instance_type":"t3.micro"},"rds":{"enabled":true,"engine":"mysql"},"public":false,"region":"ap-northeast-2"}
```

8.
- type: text
- input: `서버 여러 대만 필요`
- expected:
```json
{"vpc":true,"ec2":{"count":2,"instance_type":"t3.micro"},"rds":{"enabled":false,"engine":null},"public":false,"region":"ap-northeast-2"}
```

9.
- type: text
- input: `n. virginia, ec2 2대, db는 postgres, public`
- expected:
```json
{"vpc":true,"ec2":{"count":2,"instance_type":"t3.micro"},"rds":{"enabled":true,"engine":"postgres"},"public":true,"region":"us-east-1"}
```

10.
- type: text
- input: `서울에 app ec2 1대만`
- expected:
```json
{"vpc":true,"ec2":{"count":1,"instance_type":"t3.micro"},"rds":{"enabled":false,"engine":null},"public":false,"region":"ap-northeast-2"}
```

11.
- type: text (ambiguous)
- input: `DB는 나중에 결정`
- expected:
```json
{"vpc":true,"ec2":{"count":1,"instance_type":"t3.micro"},"rds":{"enabled":false,"engine":null},"public":false,"region":"ap-northeast-2"}
```

12.
- type: text (ambiguous)
- input: `public으로 할지 고민중이야`
- expected:
```json
{"vpc":true,"ec2":{"count":1,"instance_type":"t3.micro"},"rds":{"enabled":false,"engine":null},"public":false,"region":"ap-northeast-2"}
```

13.
- type: text
- input: `도쿄에서 ec2 4대와 mysql`
- expected:
```json
{"vpc":true,"ec2":{"count":4,"instance_type":"t3.micro"},"rds":{"enabled":true,"engine":"mysql"},"public":false,"region":"ap-northeast-1"}
```

14.
- type: text
- input: `private 네트워크에 ec2 2대, rds 없음`
- expected:
```json
{"vpc":true,"ec2":{"count":2,"instance_type":"t3.micro"},"rds":{"enabled":false,"engine":null},"public":false,"region":"ap-northeast-2"}
```

15.
- type: text
- input: `EC2 2개, DB는 postgres, 서울, public`
- expected:
```json
{"vpc":true,"ec2":{"count":2,"instance_type":"t3.micro"},"rds":{"enabled":true,"engine":"postgres"},"public":true,"region":"ap-northeast-2"}
```

16.
- type: sketch
- input: `스케치 설명: ec2 x4, rds 없음, 오하이오`
- expected:
```json
{"vpc":true,"ec2":{"count":4,"instance_type":"t3.micro"},"rds":{"enabled":false,"engine":null},"public":false,"region":"us-east-2"}
```

17.
- type: sketch
- input: `스케치 설명: 인터넷 -> ec2 1 -> rds(postgres), 버지니아`
- expected:
```json
{"vpc":true,"ec2":{"count":1,"instance_type":"t3.micro"},"rds":{"enabled":true,"engine":"postgres"},"public":true,"region":"us-east-1"}
```

18.
- type: text
- input: `ap-southeast-1 ec2 2 t3.small mysql`
- expected:
```json
{"vpc":true,"ec2":{"count":2,"instance_type":"t3.small"},"rds":{"enabled":true,"engine":"mysql"},"public":false,"region":"ap-southeast-1"}
```

19.
- type: text
- input: `서울 ec2 2, 외부 공개 안함, db는 필요없어`
- expected:
```json
{"vpc":true,"ec2":{"count":2,"instance_type":"t3.micro"},"rds":{"enabled":false,"engine":null},"public":false,"region":"ap-northeast-2"}
```

20.
- type: text
- input: `tokyo public ec2 1 mysql`
- expected:
```json
{"vpc":true,"ec2":{"count":1,"instance_type":"t3.micro"},"rds":{"enabled":true,"engine":"mysql"},"public":true,"region":"ap-northeast-1"}
```

