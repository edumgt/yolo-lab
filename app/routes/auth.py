from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from app.models import db, User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    """
    사용자 회원가입 라우트
    - GET: 가입 폼 렌더
    - POST: 사용자명 중복 체크, 비밀번호 확인 후 DB 저장
    """
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        confirm = request.form["confirm_password"]

        if password != confirm:
            flash("비밀번호가 일치하지 않습니다.", "danger")
            return render_template("register.html")

        if User.query.filter_by(username=username).first():
            flash("이미 존재하는 사용자입니다.", "danger")
            return render_template("register.html")

        # 비밀번호 해시 생성 후 저장
        user = User(username=username, password=generate_password_hash(password))
        db.session.add(user)
        db.session.commit()
        flash("회원가입 성공! 로그인 해주세요.", "success")
        return redirect(url_for('auth.login'))

    return render_template("register.html")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    """
    사용자 로그인 라우트
    - GET: 로그인 폼 렌더
    - POST: 사용자명, 비밀번호 검증
    """
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            session['username'] = username
            flash("로그인 성공!", "success")
            return redirect(url_for('main.index'))

        flash("로그인 실패. 사용자명을 확인하세요.", "danger")

    return render_template("login.html")

@auth_bp.route("/logout")
def logout():
    """
    사용자 로그아웃
    - 세션 삭제
    - 로그인 화면으로 리다이렉트
    """
    session.clear()
    flash("로그아웃 되었습니다.", "info")
    return redirect(url_for('auth.login'))
