# Flask YOLO8 Analyzer

Flask + YOLOv8 객체 탐지 웹앱 (이미지/영상 분석, S3 결과 관리)입니다.  
사용자는 로그인 후 파일을 업로드하거나 샘플 파일을 선택해 분석을 요청하고, 결과 상태를 조회/다운로드할 수 있습니다.

## 핵심 구성

| 구성 요소 | 설명 |
|---|---|
| 웹 서버 | `Flask` (`app.py`) |
| 인증/세션 | `routes/auth.py`, `Flask-Session` |
| 분석 처리 | `routes/main.py` + `Ultralytics YOLOv8` |
| 데이터 저장 | `SQLAlchemy` (`models.py`, 기본 SQLite) |
| 파일 저장 | `AWS S3` (`utils/s3_utils.py`) |
| 상태 UI | `templates/results.html`에서 `/results/status` Ajax 폴링 |

### YOLO 처리 흐름
1. 로그인 사용자만 분석 요청 가능 (`login_required_view`)
2. 입력 파일 검증 (`jpg/jpeg/png/mp4/avi/mov`)
3. DB에 `processing` 상태 기록
4. 백그라운드 스레드에서 YOLO 실행
5. 결과 파일을 S3 업로드 후 DB 상태 갱신 (`done`/`error`)
6. 결과 화면에서 Ajax 폴링으로 상태 확인

## 실행 방법

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

## 환경 변수 핵심 항목

| 변수 | 설명 | 기본값 |
|---|---|---|
| `APP_ENV` | 실행 환경 | `local` |
| `FLASK_SECRET_KEY` | Flask 세션/보안 키 | (필수 변경) |
| `FLASK_DEBUG` | 개발 디버그 여부 | `prod` 외 `true` |
| `DATABASE_URL` | DB 접속 문자열 | `sqlite:///users.db` |
| `AWS_ACCESS_KEY_ID` | AWS 인증 키 ID | - |
| `AWS_SECRET_ACCESS_KEY` | AWS 인증 시크릿 | - |
| `AWS_REGION` | AWS 리전 | `ap-northeast-2` |
| `S3_BUCKET` | 결과 저장 버킷명 | `my-bucket` |
| `UPLOAD_FOLDER` | S3 업로드 prefix | `uploads` |
| `RESULT_FOLDER` | S3 결과 prefix | `results` |
| `SAMPLE_FOLDER` | 샘플 파일 경로 | `samples` |

`.env` + `.env.{APP_ENV}` 순서로 로딩됩니다.

## GitHub Secrets / Variables 설정 가이드

아래 내용은 현재 워크플로우 코드 기준입니다.

- CI 워크플로우: `.github/workflows/python-app.yml`
  - GitHub Secrets/Variables가 필요하지 않습니다.
- CD 워크플로우: `.github/workflows/codepipeline-full.yml`
  - AWS 인증용 Secrets/Variables가 필요합니다.

### Repository Secrets (Actions)

`Settings > Secrets and variables > Actions > Secrets`에 등록

| 이름 | 필수 여부 | 값(무엇을 넣어야 하는지) | 비고 |
|---|---|---|---|
| `AWS_GITHUB_ROLE_ARN` | 권장(가능하면 필수로 사용) | GitHub OIDC로 AssumeRole할 IAM Role ARN. 예: `arn:aws:iam::<ACCOUNT_ID>:role/github-actions-codepipeline-role` | 이 값이 있으면 Access Key 방식 대신 OIDC 사용 |
| `AWS_ACCESS_KEY_ID` | 조건부 필수 | IAM User Access Key ID | `AWS_GITHUB_ROLE_ARN`이 없을 때만 필요 |
| `AWS_SECRET_ACCESS_KEY` | 조건부 필수 | IAM User Secret Access Key | `AWS_GITHUB_ROLE_ARN`이 없을 때만 필요 |

정리:
- 권장 구성: `AWS_GITHUB_ROLE_ARN`만 등록 (OIDC)
- 대체 구성: `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` 등록 (fallback)

### Repository Variables (Actions)

`Settings > Secrets and variables > Actions > Variables`에 등록

| 이름 | 필수 여부 | 값(무엇을 넣어야 하는지) | 기본 동작 |
|---|---|---|---|
| `AWS_REGION` | 선택 | CodePipeline이 있는 리전. 예: `ap-northeast-2` | 미등록 시 `ap-northeast-2` |
| `CODEPIPELINE_NAME` | 선택 | 기본 파이프라인 이름 | 미등록 시 `deploy/gitops/environments/*.json`의 `codepipeline_name` 사용 |

### 워크플로우별 사용 현황

- `python-app.yml`: Secrets/Variables 미사용
- `codepipeline-full.yml`:
  - 인증 분기:
    - `AWS_GITHUB_ROLE_ARN` 있으면 OIDC 인증 사용
    - 없으면 `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` 사용
  - 파이프라인/리전 해석:
    - 우선: `workflow_dispatch` 입력값
    - 다음: `deploy/gitops/environments/{local,dev,prod}.json`
    - 마지막 fallback: `vars.AWS_REGION`, `vars.CODEPIPELINE_NAME`

### IAM 권한(최소 권장)

워크플로우가 실제로 호출하는 API 기준 최소 권한:

- `codepipeline:GetPipeline`
- `codepipeline:StartPipelineExecution`
- `codepipeline:GetPipelineExecution`

권장 리소스 범위:
- `arn:aws:codepipeline:<region>:<account-id>:<pipeline-name>` 단위로 최소화

### OIDC Role Trust Policy 예시

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

### 자주 놓치는 포인트

- `AWS_GITHUB_ROLE_ARN`을 설정했다면 Access Key를 굳이 추가할 필요는 없습니다.
- `CODEPIPELINE_NAME`가 없어도 각 환경 JSON에 `codepipeline_name`이 있으면 동작합니다.
- `develop`/`main` 브랜치와 GitOps JSON의 `branch` 값이 다르면 배포가 실패합니다.
- GitHub Secrets에 앱 런타임 변수(`FLASK_SECRET_KEY`, `S3_BUCKET` 등)를 넣어도, 현재 워크플로우는 직접 읽지 않습니다.
  - 이 값들은 ECS Task Definition, CodeBuild 환경변수, EC2 systemd env 등 배포 타깃에 주입해야 합니다.

### 앱 런타임 변수 보관(선택)

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

## 현재 코드 기준 제약사항
- 결과 저장이 S3에 강하게 결합되어 있음 (로컬 fallback 없음)
- YOLO/업로드 예외가 광범위하게 `except Exception` 처리되어 원인 로그가 부족함
- 업로드 단계 일부 예외는 사용자에게 500으로 보일 수 있음
- 파일명 정책이 엄격하여 한글/공백/특수문자 파일명 업로드 불가

## 권장 개선사항
- S3 실패 시 로컬 저장 fallback 추가
- 예외 로깅 강화(오류 원인/스택 추적)
- 백그라운드 작업 큐(Celery/RQ)로 전환
- `/api/health`에 DB/S3 readiness 분리 (`/api/ready`) 추가

## 문서

| 문서 | 내용 |
|---|---|
| [프로젝트 구조](docs/project-structure.md) | 폴더/파일 구조 및 기술 스택 |
| [코드 흐름](docs/code-flow.md) | 인증·업로드·YOLO 분석 흐름 상세 |
| [데이터 흐름](docs/data-flow.md) | 시퀀스 다이어그램 및 데이터 저장소 구조 |
| [API 명세](docs/api-spec.md) | 엔드포인트 요청/응답 명세 |
| [Flask vs Django](docs/flask-vs-django.md) | 두 프레임워크 비교 |

### 배포 템플릿
- GitOps 프로파일: `deploy/gitops/environments/*.json`
- CI: `.github/workflows/python-app.yml`
- CD: `.github/workflows/codepipeline-full.yml`
