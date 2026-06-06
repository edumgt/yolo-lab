from flask import Flask, jsonify
from flask_session import Session
from app.models import db
from app.config import Config
from app.routes.auth import auth_bp
from app.routes.main import main_bp
from flask_migrate import Migrate

app = Flask(__name__)
app.config.from_object(Config)

# DB 마이그레이션 초기화
migrate = Migrate(app, db)
db.init_app(app)

# 세션 스토리지 (서버 측 세션)
Session(app)

# DB 테이블 생성
with app.app_context():
    db.create_all()

# 라우트 등록
app.register_blueprint(auth_bp)
app.register_blueprint(main_bp)


@app.get("/api/health")
def health_check():
    return jsonify({"status": "ok", "app_env": app.config.get("APP_ENV", "local")})
