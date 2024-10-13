# app/utils/db_util.py
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from app.config.app_config import AppConfig

db = SQLAlchemy()


def init_app(app: Flask):
    config_loader = AppConfig()
    db_config = config_loader.get_database_config()

    app.config[
        'SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['dbname']}"
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_ECHO'] = db_config.get('echo', False)
    app.config['SQLALCHEMY_POOL_SIZE'] = db_config.get('pool_size', 5)
    app.config['SQLALCHEMY_MAX_OVERFLOW'] = db_config.get('max_overflow', 10)
    app.config['SQLALCHEMY_POOL_RECYCLE'] = db_config.get('pool_recycle', 3600)

    db.init_app(app)


def get_db():
    return db
