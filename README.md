# Flask YOLO8 Analyzer

Flask + YOLOv8 기반 이미지/영상 객체 탐지 웹 애플리케이션입니다.  
사용자는 로그인 후 파일을 업로드하거나 샘플 파일을 선택해 분석을 요청하고, 결과 상태를 조회/다운로드할 수 있습니다.

## 1) 레포 분석 요약

### 핵심 구성
- 웹 서버: `Flask` (`app.py`)
- 인증/세션: `routes/auth.py`, `Flask-Session`
- 분석 처리: `routes/main.py` + `Ultralytics YOLO`
- 데이터 저장: `SQLAlchemy` (`models.py`, 기본 SQLite)
- 파일 저장: `AWS S3` (`utils/s3_utils.py`)
- 상태 UI: `templates/results.html`에서 `/results/status` 폴링

### YOLO 처리 흐름
1. 로그인 사용자만 분석 요청 가능 (`login_required_view`)
2. 입력 파일 검증 (`jpg/jpeg/png/mp4/avi/mov`)
3. DB에 `processing` 상태 기록
4. 백그라운드 스레드에서 YOLO 실행
5. 결과 파일을 S3 업로드 후 DB 상태 갱신 (`done`/`error`)
6. 결과 화면에서 Ajax 폴링으로 상태 확인

## 2) 실행 검증 결과 (2026-03-11 기준)

### 검증 환경
- Python: `3.12.3`
- 의존성: `requirements.txt` 기준 `.venv` 설치 완료

### 실제 확인한 항목
- 의존성 import: 성공 (`flask`, `ultralytics`, `flask_sqlalchemy`, `flask_session`, `boto3`, `dotenv`)
- Flask test client 헬스체크:
  - `GET /api/health` -> `200`
  - 응답: `{"status":"ok","app_env":"local"}`
- 인증 플로우:
  - `POST /register` -> `302 /login`
  - `POST /login` -> `302 /`
- YOLO 샘플 추론:
  - 입력: `samples/highway-7213206_1280.jpg`
  - 실행 로그: `13 cars` 탐지
- 분석 요청 상태 전이:
  - 초기: `processing`
  - 이후: `error` (S3 업로드 단계에서 실패한 것으로 판단)

### 실행 가능성 결론
- 코드/의존성/YOLO 추론 자체는 동작 확인됨.
- 이 앱은 **S3 의존 구조**라서 AWS 설정 없이는 결과 완료(`done`)까지 가기 어렵고 `error`로 끝날 수 있음.
- 현재 샌드박스에서는 포트 바인딩 제한으로 실제 `0.0.0.0:8000` 리슨 검증은 제한됨.
  - Flask `test_client`로는 정상 라우팅 확인 완료.

## 3) YOLO 기반으로 할 수 있는 작업

### 현재 이 레포에서 직접 지원하는 작업

#### A. 이미지 객체 탐지
- 입력: `jpg/jpeg/png`
- 처리: `model(input_path)`로 단일 이미지 추론
- 결과: 바운딩 박스가 그려진 결과 이미지 생성 후 S3 업로드

#### B. 영상 객체 탐지
- 입력: `mp4/avi/mov`
- 처리: `model.predict(source=..., save=True, ...)`로 프레임 단위 추론
- 결과: 추론 결과 영상 파일 생성 후 S3 업로드

#### C. 비동기 분석 상태 관리
- 요청 직후 DB 상태를 `processing`으로 저장
- 백그라운드 완료 시 `done`/예외 시 `error` 갱신
- `/results/status`로 실시간 상태 폴링

#### D. 사용자별 결과 이력 관리
- 사용자명 기준으로 결과 목록 정렬 조회
- 완료 건은 presigned URL 기반 다운로드 제공

### YOLO 계열 모델로 확장 가능한 주요 AI 작업

> 현재 코드베이스는 `routes/main.py`에서 `yolov8n.pt`를 사용한 **객체 탐지(detect)** 흐름만 구현되어 있습니다.  
> 아래 항목은 YOLO 계열 모델로 확장 가능한 대표 작업이며, 분류/세그멘테이션/포즈/추적/OBB는 현재 레포에 아직 구현되어 있지 않습니다.

#### E. 이미지 분류
- 전체 이미지를 하나의 클래스(예: 고양이, 개, 자동차)로 분류
- 활용 예: 의료 영상 1차 판독, 제품 종류 판별, 품질 검사 자동화

#### F. 세그멘테이션
- 픽셀 단위로 객체 영역을 분리
- 활용 예: 종양 영역 추출, 작물/잡초 분리, 로봇 비전

#### G. 포즈 추정
- 사람의 관절 위치를 추정해 자세와 동작을 인식
- 활용 예: 스포츠 분석, 작업자 안전 모니터링, AR/VR 인터랙션

#### H. 객체 추적
- 영상에서 동일 객체를 프레임 간 연속 추적
- 활용 예: 교통량 분석, 군중 모니터링, 리테일 고객 동선 분석

#### I. OBB(회전 바운딩 박스) 탐지
- 회전된 객체의 방향까지 포함해 탐지
- 활용 예: 항공/위성 영상의 건물·항공기 탐지, 물류 박스 정렬 상태 확인

### 산업별 활용 예시

| 분야 | YOLO 활용 |
| --- | --- |
| 자율주행 | 차량·보행자·신호등 실시간 탐지 |
| 제조업 | 불량품 검출, 품질 관리 |
| 의료 | CT/MRI 영상 분석, 병변 탐지 |
| 보안 | CCTV 침입 탐지, 얼굴/객체 인식 보조 |
| 농업 | 작물 모니터링, 병해충 탐지 |
| 스포츠 | 선수 동작 추적, 경기 분석 |

### 장점과 한계

#### 장점
- 실시간 처리에 적합하며 모델 크기와 하드웨어에 따라 대략 30~300 FPS 수준의 추론 환경 구성이 가능
- GPU/CPU/모바일 등 다양한 하드웨어에서 운용 가능
- 오픈소스 생태계가 성숙해 빠른 PoC와 서비스 적용에 유리

#### 한계
- 작은 객체나 매우 밀집된 장면에서는 정확도가 떨어질 수 있음
- 학습 데이터와 실제 운영 데이터의 분포가 다르면 오탐·미탐이 증가하는 등 성능 저하가 발생할 수 있음
- 이 레포처럼 기본 `detect` 모델만 연결된 경우, 다른 작업은 별도 모델/후처리/UI 설계가 추가로 필요

## 4) YOLO 기반으로 확인 가능한 항목 (운영/QA 체크리스트)

### 기능 확인
- 파일 확장자 제한이 정상 동작하는지
- 파일명 정책(영문/숫자/`._-`) 위반 시 차단되는지
- 샘플 파일 선택 시 분석이 시작되는지
- 분석 상태가 `processing -> done/error`로 전이되는지

### 추론 품질 확인
- 샘플 이미지/영상에서 기대 객체가 탐지되는지
- 탐지 개수/신뢰도(confidence)가 상식적으로 타당한지
- 다양한 해상도/조명/밀집도 데이터에서 오탐/미탐 비율 추세

### 성능 확인
- 이미지 1건당 추론 시간
- 영상 길이 대비 총 처리 시간
- 동시 요청 시 스레드 기반 처리 안정성

### 저장/다운로드 확인
- S3 업로드 성공 여부
- presigned URL 다운로드 가능 여부
- 만료 시간 이후 URL 접근 차단 여부

## 5) 실행 방법

### 로컬 Python 실행
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
cp .env.local.example .env.local

# 중요: Ultralytics 설정 폴더 권한 문제가 있으면 아래 변수 지정
export XDG_CONFIG_HOME=$(pwd)/.config

APP_ENV=local FLASK_DEBUG=false python app.py
```

### Docker 실행
```bash
cp .env.local.example .env.local
docker compose --env-file .env.local up -d --build
```

중지:
```bash
docker compose down
```

## 6) 환경 변수 핵심 항목
- `APP_ENV`: `local`/`dev`/`prod`
- `FLASK_SECRET_KEY`: Flask 세션/보안 키
- `FLASK_DEBUG`: 개발 디버그 여부
- `DATABASE_URL`: 기본 `sqlite:///users.db`
- `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`
- `S3_BUCKET`
- `UPLOAD_FOLDER`, `RESULT_FOLDER`, `SAMPLE_FOLDER`

`.env` + `.env.{APP_ENV}` 순서로 로딩됩니다.

## 7) GitHub Secrets / Variables 설정 가이드 (상세)

아래 내용은 현재 워크플로우 코드 기준입니다.

- CI 워크플로우: `.github/workflows/python-app.yml`
  - GitHub Secrets/Variables가 필요하지 않습니다.
- CD 워크플로우: `.github/workflows/codepipeline-full.yml`
  - AWS 인증용 Secrets/Variables가 필요합니다.

### 7-1. Repository Secrets (Actions)

`Settings > Secrets and variables > Actions > Secrets`에 등록

| 이름 | 필수 여부 | 값(무엇을 넣어야 하는지) | 비고 |
|---|---|---|---|
| `AWS_GITHUB_ROLE_ARN` | 권장(가능하면 필수로 사용) | GitHub OIDC로 AssumeRole할 IAM Role ARN. 예: `arn:aws:iam::<ACCOUNT_ID>:role/github-actions-codepipeline-role` | 이 값이 있으면 Access Key 방식 대신 OIDC 사용 |
| `AWS_ACCESS_KEY_ID` | 조건부 필수 | IAM User Access Key ID | `AWS_GITHUB_ROLE_ARN`이 없을 때만 필요 |
| `AWS_SECRET_ACCESS_KEY` | 조건부 필수 | IAM User Secret Access Key | `AWS_GITHUB_ROLE_ARN`이 없을 때만 필요 |

정리:
- 권장 구성: `AWS_GITHUB_ROLE_ARN`만 등록 (OIDC)
- 대체 구성: `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` 등록 (fallback)

### 7-2. Repository Variables (Actions)

`Settings > Secrets and variables > Actions > Variables`에 등록

| 이름 | 필수 여부 | 값(무엇을 넣어야 하는지) | 기본 동작 |
|---|---|---|---|
| `AWS_REGION` | 선택 | CodePipeline이 있는 리전. 예: `ap-northeast-2` | 미등록 시 `ap-northeast-2` |
| `CODEPIPELINE_NAME` | 선택 | 기본 파이프라인 이름 | 미등록 시 `deploy/gitops/environments/*.json`의 `codepipeline_name` 사용 |

### 7-3. 실제로 어떤 워크플로우에서 쓰는가

- `python-app.yml`: Secrets/Variables 미사용
- `codepipeline-full.yml`:
  - 인증 분기:
    - `AWS_GITHUB_ROLE_ARN` 있으면 OIDC 인증 사용
    - 없으면 `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` 사용
  - 파이프라인/리전 해석:
    - 우선: `workflow_dispatch` 입력값
    - 다음: `deploy/gitops/environments/{local,dev,prod}.json`
    - 마지막 fallback: `vars.AWS_REGION`, `vars.CODEPIPELINE_NAME`

### 7-4. IAM 권한(최소 권장)

워크플로우가 실제로 호출하는 API 기준 최소 권한:

- `codepipeline:GetPipeline`
- `codepipeline:StartPipelineExecution`
- `codepipeline:GetPipelineExecution`

권장 리소스 범위:
- `arn:aws:codepipeline:<region>:<account-id>:<pipeline-name>` 단위로 최소화

### 7-5. OIDC Role Trust Policy 예시

`AWS_GITHUB_ROLE_ARN` 방식을 쓸 때 IAM Role 신뢰 정책에 GitHub OIDC 주체를 허용해야 합니다.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Federated": "arn:aws:iam::<ACCOUNT_ID>:oidc-provider/token.actions.githubusercontent.com"
      },
      "Action": "sts:AssumeRoleWithWebIdentity",
      "Condition": {
        "StringEquals": {
          "token.actions.githubusercontent.com:aud": "sts.amazonaws.com"
        },
        "StringLike": {
          "token.actions.githubusercontent.com:sub": [
            "repo:<OWNER>/<REPO>:ref:refs/heads/develop",
            "repo:<OWNER>/<REPO>:ref:refs/heads/main"
          ]
        }
      }
    }
  ]
}
```

`<OWNER>/<REPO>`는 현재 저장소로 바꿔야 합니다.

### 7-6. 자주 놓치는 포인트

- `AWS_GITHUB_ROLE_ARN`을 설정했다면 Access Key를 굳이 추가할 필요는 없습니다.
- `CODEPIPELINE_NAME`가 없어도 각 환경 JSON에 `codepipeline_name`이 있으면 동작합니다.
- `develop`/`main` 브랜치와 GitOps JSON의 `branch` 값이 다르면 배포가 실패합니다.
- GitHub Secrets에 앱 런타임 변수(`FLASK_SECRET_KEY`, `S3_BUCKET` 등)를 넣어도, 현재 워크플로우는 직접 읽지 않습니다.
  - 이 값들은 ECS Task Definition, CodeBuild 환경변수, EC2 systemd env 등 배포 타깃에 주입해야 합니다.

### 7-7. 앱 런타임 변수까지 GitHub에 보관하려는 경우(선택)

현재 워크플로우에서 직접 읽지는 않지만, 중앙 보관 목적으로 GitHub Secrets에 저장할 수 있는 항목입니다.

| 이름 | 무엇을 넣어야 하는지 | 주입 대상(실행 위치) |
|---|---|---|
| `FLASK_SECRET_KEY` | Flask 세션 서명용 강력한 랜덤 문자열 | 컨테이너/서버 환경변수 |
| `DATABASE_URL` | DB 접속 문자열. 예: `sqlite:///users.db` 또는 RDS URI | 컨테이너/서버 환경변수 |
| `AWS_ACCESS_KEY_ID` | 앱이 S3 업로드할 IAM Access Key ID | 컨테이너/서버 환경변수 |
| `AWS_SECRET_ACCESS_KEY` | 앱이 S3 업로드할 IAM Secret Access Key | 컨테이너/서버 환경변수 |
| `AWS_REGION` | S3 리전. 예: `ap-northeast-2` | 컨테이너/서버 환경변수 |
| `S3_BUCKET` | 결과 파일을 저장할 버킷명 | 컨테이너/서버 환경변수 |
| `UPLOAD_FOLDER` | 업로드 원본 키 prefix. 기본 `uploads` | 컨테이너/서버 환경변수 |
| `RESULT_FOLDER` | 결과 파일 키 prefix. 기본 `results` | 컨테이너/서버 환경변수 |
| `SAMPLE_FOLDER` | 샘플 파일 경로. 기본 `samples` | 컨테이너/서버 환경변수 |

주의:
- CI/CD용 AWS 인증(`AWS_GITHUB_ROLE_ARN` 또는 Access Key)과 앱 런타임용 AWS 키를 같은 계정/권한으로 섞지 않는 것을 권장합니다.
- 앱 런타임 IAM 권한은 최소한 `s3:PutObject`, `s3:GetObject`(presign 대상), 필요 시 `s3:ListBucket` 범위로 제한하세요.

## 8) 현재 코드 기준 제약사항
- 결과 저장이 S3에 강하게 결합되어 있음 (로컬 fallback 없음)
- YOLO/업로드 예외가 광범위하게 `except Exception` 처리되어 원인 로그가 부족함
- 업로드 단계 일부 예외는 사용자에게 500으로 보일 수 있음
- 파일명 정책이 엄격하여 한글/공백/특수문자 파일명 업로드 불가

## 9) 권장 개선사항
- S3 실패 시 로컬 저장 fallback 추가
- 예외 로깅 강화(오류 원인/스택 추적)
- 백그라운드 작업 큐(Celery/RQ)로 전환
- `/api/health`에 DB/S3 readiness 분리 (`/api/ready`) 추가

## 10) 문서/배포 템플릿
- GitOps 프로파일: `deploy/gitops/environments/*.json`
- CI: `.github/workflows/python-app.yml`
- CD: `.github/workflows/codepipeline-full.yml`


---

# Flask와 Django의 차이

## 개요
Flask와 Django의 가장 큰 차이는 **가볍게 필요한 것만 붙이는 방식**인지, 아니면 **처음부터 웹서비스에 필요한 기능이 상당수 포함된 방식**인지에 있습니다.

- **Flask**: 마이크로 프레임워크, 작고 유연함
- **Django**: 풀스택 프레임워크, 기능이 많이 기본 제공됨

---

## Flask

Flask는 아주 가벼운 Python 웹 프레임워크입니다.  
기본적으로 라우팅, 요청/응답 처리 같은 핵심 기능만 제공하고, 나머지는 필요할 때 확장 라이브러리를 붙여서 사용합니다.

예를 들면 다음과 같습니다.

- ORM: SQLAlchemy
- 관리자 화면: 별도 패키지
- 인증: 직접 구현하거나 확장 라이브러리 사용

### Flask의 장점
- 구조를 자유롭게 설계할 수 있음
- 작은 서비스, API 서버, 프로토타입 개발에 적합
- 개발자가 원하는 방식으로 아키텍처를 구성 가능
- AI/ML 백엔드처럼 경량 서버에 잘 어울림

### Flask의 단점
- 프로젝트가 커질수록 규칙을 직접 잘 잡아야 함
- 인증, 관리자, ORM 같은 기능을 직접 선택하고 조합해야 함
- 팀 단위 개발에서는 스타일이 제각각이 될 수 있음

---

## Django

Django는 웹서비스 개발에 필요한 기능을 상당수 기본 제공하는 Python 웹 프레임워크입니다.

기본 제공 기능 예시는 다음과 같습니다.

- ORM
- Admin 페이지
- 인증/권한 관리
- 폼 처리
- 보안 기능(CSRF, XSS 대응 구조 등)
- 프로젝트 구조 규칙

### Django의 장점
- 관리자 시스템, 회원 기능, 게시판 같은 기능을 빠르게 만들기 좋음
- 팀 개발 시 구조가 통일되기 쉬움
- 업무 시스템, ERP, CRM, 백오피스 개발에 강함
- 기본 기능이 풍부해서 생산성이 높음

### Django의 단점
- Flask보다 무겁게 느껴질 수 있음
- 자유도가 상대적으로 낮음
- 아주 단순한 API만 만드는 경우에는 오버스펙일 수 있음

---

## 비유로 이해하기

- **Flask** = 레고 부품 상자  
  필요한 부품을 골라서 직접 조립하는 방식
- **Django** = 조립식 가구 세트  
  필요한 구성품이 대부분 이미 포함된 방식

---

## 어떤 경우에 적합한가

### Flask가 더 적합한 경우
- 간단한 REST API
- 경량 마이크로서비스
- AI/ML 백엔드
- 빠른 실험용 프로젝트
- 구조를 직접 설계하고 싶은 경우

### Django가 더 적합한 경우
- 관리자 페이지가 중요한 업무 시스템
- 회원가입/로그인/권한 관리가 필요한 사이트
- 게시판, 쇼핑몰, ERP, CRM 같은 웹서비스
- 팀 단위로 빠르게 표준화된 구조가 필요한 경우

---

## 개발 스타일 차이

- **Flask**: 자유롭고 가벼움, 대신 직접 정해야 할 것이 많음
- **Django**: 규칙이 있고 생산성이 높음, 대신 틀이 어느 정도 정해져 있음

---

## 성능 관점

성능은 단순히 Flask가 무조건 빠르고 Django가 무조건 느리다고 보기는 어렵습니다.  
실제 서비스에서는 다음 요소들이 더 큰 영향을 줍니다.

- 데이터베이스 설계
- 캐시 사용 여부
- 비동기 처리 구조
- 배포 환경 및 인프라 구성

다만 일반적으로는 다음처럼 느껴질 수 있습니다.

- Flask는 기본 구성이 가벼워서 작은 서비스에 적합
- Django는 기본 기능이 많아 초기 구조가 조금 더 무겁게 느껴질 수 있음

---

## 추천 정리

- **혼자 빠르게 API 또는 AI 서버 만들기** → Flask
- **관리자/회원/DB 중심의 웹서비스 만들기** → Django

---

## 한눈에 보는 비교표

| 항목 | Flask | Django |
|---|---|---|
| 성격 | 마이크로 프레임워크 | 풀스택 프레임워크 |
| 기본 제공 기능 | 적음 | 많음 |
| 자유도 | 매우 높음 | 비교적 높지만 구조화됨 |
| 학습 방식 | 작게 시작 가능 | 체계적으로 익혀야 함 |
| 관리자 기능 | 기본 없음 | 기본 제공 |
| ORM | 기본 없음 | 기본 제공 |
| 인증/권한 | 직접 구성 필요 | 기본 제공 |
| 적합한 프로젝트 | API, 마이크로서비스, AI 서버 | 관리자 시스템, 게시판, ERP, CRM |