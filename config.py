from importlib.resources import path
import os
from dotenv import load_dotenv

env_path = os.path.join(os.path.dirname(__file__), '.env')

if os.path.exists(env_path):
    print(f"Loading environment variables from {env_path}")
    load_dotenv(env_path)
else:
    print(f"Warning: .env file not found at {env_path}. Using system environment variables.")

DB_TYPE = os.getenv("DB_TYPE", "sqlite").lower()

# import os

# app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'app.db')


def get_database_uri():
    if DB_TYPE == "sqlite":
        basedir = os.path.abspath(os.path.dirname(__file__))
        return f"sqlite:///{os.path.join(basedir, 'app.db')}"

    elif DB_TYPE == "mysql":
        user     = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        host     = os.getenv("DB_HOST")
        port     = os.getenv("DB_PORT", 3306)
        name     = os.getenv("DB_NAME")
        return f"mysql+pymysql://{user}:{password}@{host}:{port}/{name}"

    elif DB_TYPE == "postgres":
        user     = os.getenv("DB_USER")
        password = os.getenv("DB_PASSWORD")
        host     = os.getenv("DB_HOST")
        port     = os.getenv("DB_PORT", 5432)
        name     = os.getenv("DB_NAME")
        return f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{name}"

    elif DB_TYPE == "supabase":
        # Use the full connection string from Supabase dashboard
        # Project Settings → Database → Connection string → URI
        return os.getenv("SUPABASE_URL")

    else:
        raise ValueError(f'Unsupported DB_TYPE: "{DB_TYPE}". Use sqlite, mysql, postgres, or supabase.')

class Config:
    SQLALCHEMY_DATABASE_URI = get_database_uri()
    SECRET_KEY = os.getenv("SECRET_KEY", "default_secret_key")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = os.getenv("MAIL_SERVER", "sandbox.smtp.mailtrap.io")
    MAIL_PORT = int(os.getenv("MAIL_PORT", 2525))
    MAIL_USE_TLS = os.getenv("MAIL_USE_TLS", "true").lower() in ["true", "1", "t"]
    MAIL_USE_SSL = os.getenv("MAIL_USE_SSL", "false").lower() in ["true", "1", "t"]
    MAIL_USERNAME = os.getenv("MAIL_USERNAME", "35ac86847482e9")
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD", "e4ff6eb89fad")
    REMEMBER_COOKIE_DURATION = 1800  # 30 minutes


class DevelopmentConfig(Config):
    DEBUG = True

class ProductionConfig(Config):
    DEBUG = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

