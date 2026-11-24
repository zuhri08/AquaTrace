import re
from functools import wraps

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash

from app import db
from app.models import User

auth_bp = Blueprint("auth", __name__)
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Silakan masuk untuk melanjutkan.", "info")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped


def role_required(*allowed_roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if g.user.role not in allowed_roles:
                return render_template("errors/403.html"), 403
            return view(*args, **kwargs)

        return wrapped

    return decorator


def _dashboard_for(user):
    return {
        "warga": "warga.dashboard",
        "petugas_lab": "pages.petugas_dashboard",
        "admin": "pages.admin_dashboard",
    }[user.role]


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if g.user is not None:
        return redirect(url_for(_dashboard_for(g.user)))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()
        if user is None or not user.aktif or not check_password_hash(
            user.password_hash, password
        ):
            flash("Email atau kata sandi tidak sesuai, atau akun tidak aktif.", "error")
            return render_template("auth/login.html"), 401

        session.clear()
        session["user_id"] = user.id
        return redirect(url_for(_dashboard_for(user)))

    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if g.user is not None:
        return redirect(url_for(_dashboard_for(g.user)))

    if request.method == "POST":
        nama = request.form.get("nama", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        errors = []
        if not nama or len(nama) > 120:
            errors.append("Nama wajib diisi (maksimal 120 karakter).")
        if not EMAIL_PATTERN.fullmatch(email) or len(email) > 255:
            errors.append("Masukkan alamat email yang valid.")
        if len(password) < 8:
            errors.append("Kata sandi harus memiliki minimal 8 karakter.")
        if User.query.filter_by(email=email).first():
            errors.append("Email tersebut sudah terdaftar.")
        if errors:
            for error in errors:
                flash(error, "error")
            return render_template("auth/register.html"), 400

        user = User(
            nama=nama,
            email=email,
            password_hash=generate_password_hash(password),
            role="warga",
            aktif=True,
        )
        db.session.add(user)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
            flash("Email tersebut sudah terdaftar.", "error")
            return render_template("auth/register.html"), 400

        session.clear()
        session["user_id"] = user.id
        flash("Akun berhasil dibuat.", "success")
        return redirect(url_for("warga.dashboard"))

    return render_template("auth/register.html")


@auth_bp.post("/logout")
@login_required
def logout():
    session.clear()
    flash("Anda telah keluar.", "info")
    return redirect(url_for("pages.landing"))
