import os

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect
from sqlalchemy import event
from sqlalchemy.engine import Engine

db = SQLAlchemy()
csrf = CSRFProtect()


@event.listens_for(Engine, "connect")
def _enable_sqlite_foreign_keys(connection, _):
    if connection.__class__.__module__.startswith("sqlite3"):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object("config.Config")
    if test_config:
        app.config.update(test_config)
    os.makedirs(app.instance_path, exist_ok=True)
    db.init_app(app)
    csrf.init_app(app)

    with app.app_context():
        from app import models  # noqa: F401
        from app.routes.auth import auth_bp
        from app.routes.admin import admin_bp
        from app.routes.api import api_bp
        from app.routes.iot import iot_bp
        from app.routes.pages import pages_bp
        from app.routes.warga import warga_bp
        from app.routes.petugas import petugas_bp

        app.register_blueprint(auth_bp)
        app.register_blueprint(admin_bp)
        app.register_blueprint(api_bp)
        app.register_blueprint(iot_bp)
        app.register_blueprint(pages_bp)
        app.register_blueprint(warga_bp)
        app.register_blueprint(petugas_bp)

    @app.before_request
    def load_logged_in_user():
        from flask import g, session

        from app.models import User

        user_id = session.get("user_id")
        g.user = db.session.get(User, user_id) if user_id else None
        if g.user is not None and not g.user.aktif:
            session.clear()
            g.user = None

    @app.context_processor
    def inject_user():
        from flask import g

        return {"current_user": getattr(g, "user", None)}

    @app.errorhandler(403)
    def forbidden(_error):
        from flask import render_template

        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(_error):
        from flask import render_template

        return render_template("errors/404.html"), 404

    return app
