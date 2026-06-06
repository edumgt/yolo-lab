from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    """
    사용자 계정 정보 테이블
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)

class Result(db.Model):
    """
    YOLO 처리 결과 테이블
    """
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    original_filename = db.Column(db.String(200), nullable=False)
    result_path = db.Column(db.String(200), nullable=True)
    result_type = db.Column(db.String(20), nullable=True)
    result_ext = db.Column(db.String(20), nullable=True)
    status = db.Column(db.String(20), default='processing')
    timestamp = db.Column(db.DateTime, server_default=db.func.now())
