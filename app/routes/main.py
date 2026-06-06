from flask import Blueprint, render_template, request, session, redirect, url_for, current_app, flash, jsonify, Flask
from werkzeug.utils import secure_filename
from ultralytics import YOLO
from app.models import db, Result
from app.utils.file_utils import is_image, is_video
from app.utils.s3_utils import upload_file, generate_presigned_url
import os, uuid, threading, tempfile
import re

main_bp = Blueprint('main', __name__)

# YOLO 모델 초기화
model = YOLO("yolov8n.pt")

def login_required_view(func):
    """
    로그인 여부를 검사하는 데코레이터
    - 세션에 username 없으면 로그인 페이지로 리다이렉트
    """
    def wrapper(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('auth.login'))
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

@main_bp.route("/download/<path:filename>")
@login_required_view
def download(filename):
    """Generate a presigned URL for the result file and redirect."""
    filename = filename.replace('\\', '/')
    bucket = current_app.config['S3_BUCKET']
    key = f"{current_app.config['RESULT_FOLDER']}/{filename}"
    url = generate_presigned_url(bucket, key)
    if url:
        return redirect(url)
    flash("파일을 찾을 수 없습니다.", "danger")
    return redirect(url_for('main.results'))

@main_bp.route("/results/status")
@login_required_view
def results_status():
    """
    로그인 사용자의 처리 결과 상태를 JSON으로 반환
    - Ajax polling 용도
    """
    username = session.get("username")
    prefix = current_app.config['RESULT_FOLDER'].rstrip('/')
    results = Result.query.filter_by(username=username).order_by(Result.timestamp.desc()).all()

    response = []
    for r in results:
        item = {
            'id': r.id,
            'filename': r.original_filename,
            'status': r.status,
            'result_type': r.result_type,
            'download_url': None
        }
        if r.status == 'done' and r.result_path:
            if r.result_path.startswith(prefix):
                filename_only = r.result_path[len(prefix):].lstrip('/')
            else:
                filename_only = r.result_path
            item['download_url'] = url_for('main.download', filename=filename_only)
        response.append(item)

    return jsonify(response)

@main_bp.route("/results")
@login_required_view
def results():
    """
    로그인 사용자의 처리 결과 목록 렌더링
    - HTML 템플릿
    """
    username = session.get("username")
    results = Result.query.filter_by(username=username).order_by(Result.timestamp.desc()).all()
    prefix = current_app.config['RESULT_FOLDER'].rstrip('/')

    for r in results:
        if r.result_path and r.result_path.startswith(prefix):
            r.download_filename = r.result_path[len(prefix):].lstrip('/')
        else:
            r.download_filename = None

    return render_template("results.html", videos=results, username=username, result_folder=prefix)

def run_yolo_in_background(app: Flask, result_record_id, input_path, filename, ext):
    """
    YOLO 모델을 백그라운드에서 실행하는 함수
    - 이미지/비디오 판별
    - 예측 결과 생성 및 저장
    - 처리 상태 DB 갱신
    """
    with app.app_context():
        result_record = Result.query.get(result_record_id)
        bucket = app.config['S3_BUCKET']
        prefix = app.config['RESULT_FOLDER'].rstrip('/')
        try:
            result_key = None
            result_type = None

            if is_image(filename):
                result_filename = f"{uuid.uuid4().hex}.{ext}"
                fd, local_path = tempfile.mkstemp(suffix=f".{ext}")
                os.close(fd)
                results = model(input_path)
                results[0].save(filename=local_path)
                result_type = 'image'
                result_key = f"{prefix}/{result_filename}"
                upload_file(local_path, bucket, result_key)
                os.remove(local_path)

            elif is_video(filename):
                temp_dir = tempfile.mkdtemp()
                model.predict(source=input_path, save=True, project=temp_dir, name='predict', exist_ok=True)
                prediction_dir = os.path.join(temp_dir, 'predict')

                for f in os.listdir(prediction_dir):
                    if is_video(f):
                        local_path = os.path.join(prediction_dir, f)
                        result_type = 'video'
                        ext = f.rsplit('.', 1)[1].lower()
                        result_filename = f"{uuid.uuid4().hex}.{ext}"
                        result_key = f"{prefix}/{result_filename}"
                        upload_file(local_path, bucket, result_key)
                        break

            if result_key and result_type:
                result_record.result_path = result_key
                result_record.result_type = result_type
                result_record.result_ext = ext
                result_record.status = 'done'
            else:
                result_record.status = 'error'

        except Exception:
            result_record.status = 'error'

        db.session.commit()

@main_bp.route("/", methods=["GET", "POST"])
@login_required_view
def index():
    """
    메인 화면 라우트
    - GET: 업로드/샘플 선택 화면
    - POST: 업로드 or 샘플 선택 → YOLO 처리 스레드 시작
    """
    username = session.get("username")
    sample_files = os.listdir(current_app.config['SAMPLE_FOLDER'])

    if request.method == "POST":
        file_select = request.form.get("fileSelect")

        if file_select == "new":
            # 사용자가 새 파일 업로드
            uploaded_file = request.files.get("video")
            if not uploaded_file or uploaded_file.filename == "":
                flash("파일이 선택되지 않았습니다.", "danger")
                return redirect(url_for('main.index'))

            filename = secure_filename(uploaded_file.filename)
            ext = filename.rsplit('.', 1)[1].lower()

            # 파일명에 한글, 공백, 특수문자 포함 여부 검사
            # 영문, 숫자, 점(.), 하이픈(-), 언더바(_)만 허용
            # 정규표현식: 한글, 공백, 기타 특수문자 포함 시 업로드 거부
            if re.search(r'[^A-Za-z0-9._-]', uploaded_file.filename):
                flash("파일명에는 영문, 숫자, 점(.), 하이픈(-), 언더바(_)만 사용할 수 있습니다.", "danger")
                return redirect(url_for('main.index'))

            if not (is_image(filename) or is_video(filename)):
                flash("지원하지 않는 파일 형식입니다.", "danger")
                return redirect(url_for('main.index'))

            temp_dir = tempfile.mkdtemp()
            save_path = os.path.join(temp_dir, filename)
            uploaded_file.save(save_path)
            bucket = current_app.config['S3_BUCKET']
            prefix = current_app.config['UPLOAD_FOLDER'].rstrip('/')
            upload_file(save_path, bucket, f"{prefix}/{filename}")
            input_path = save_path

        else:
            # 샘플 파일 선택
            filename = secure_filename(file_select)
            ext = filename.rsplit('.', 1)[1].lower()
            input_path = os.path.join(current_app.config['SAMPLE_FOLDER'], filename)

            if not os.path.exists(input_path):
                flash("선택한 샘플 파일이 존재하지 않습니다.", "danger")
                return redirect(url_for('main.index'))

        # 처리 기록 DB에 저장
        result_record = Result(
            username=username,
            original_filename=filename,
            status='processing'
        )
        db.session.add(result_record)
        db.session.commit()

        # YOLO 처리 스레드 시작
        app_ctx = current_app._get_current_object()
        thread = threading.Thread(
            target=run_yolo_in_background,
            args=(app_ctx, result_record.id, input_path, filename, ext)
        )
        thread.start()

        return redirect(url_for('main.results'))

    return render_template("index.html", sample_files=sample_files, username=username)
