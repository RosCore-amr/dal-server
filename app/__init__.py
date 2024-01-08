from flask import Flask
from flask_jwt_extended import JWTManager
from flask_babel import Babel
from flask_cors import CORS
from .database import *
from .rest_api import *

from waitress import serve


class FlaskApp:
    jwt = JWTManager()

    def __init__(self) -> None:
        # INIT APP
        self.app = Flask(__name__)
        self.app.config["CORS_HEADERS"] = "application/json"
        self.cors = CORS(self.app)

        # INIT JWT
        self.app.config["JWT_SECRET_KEY"] = "jwt-secret-string"
        self.app.config["JWT_BLACKLIST_ENABLED"] = True
        self.app.config["JWT_BLACKLIST_TOKEN_CHECKS"] = ["access", "refresh"]
        self.jwt.init_app(self.app)

        # LOADING LANGUAGE FOR ALL USER
        self.app.config["LANGUAGES"] = ["en", "vi", "ko", "ja"]
        self.babel = Babel(self.app)

        # INIT REST API
        api.init_app(self.app)
        print("RestAPI ready")

    def initDatabase(self, cfg: dict):
        """
        "host"      : '127.0.0.1',
        "port"      : 3306,
        "user"      : 'rostek',
        "pass"      : 'rostek2019',
        "scheme"    : 'seehan'
        """
        # INIT DATABASE
        SQL_URI = f"mysql://{cfg['user']}:{cfg['pass']}@{cfg['host']}:{cfg['port']}/{cfg['scheme']}"
        self.app.config["SQLALCHEMY_DATABASE_URI"] = SQL_URI
        self.app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
        self.app.config["SQLALCHEMY_POOL_SIZE"] = 20
        db.init_app(self.app)
        with self.app.app_context():
            db.create_all()
        print("Database ready")

    def start(self, flask_cfg: dict):
        """
        "host"  : '192.168.1.81',
        "port"  : 5500
        """
        serve(self.app, **flask_cfg)

    @staticmethod
    @jwt.token_in_blocklist_loader
    def checkBlocklist(jwt_header, jwt_payload):
        jti = jwt_payload["jti"]
        token = DB_RevokedToken.findById(jti)
        if token:
            return True
        return False
