import os
# from dotenv import load_dotenv

# env_path = os.path.join(os.path.dirname(__file__), '.env')

# if os.path.exists(env_path):
#     load_dotenv(env_path)


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default secret')
    # other config options can go here
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///overtime.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'sandbox.smtp.mailtrap.io')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 2525))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', '1', 't']
    MAIL_USE_SSL = os.environ.get('MAIL_USE_SSL', 'false').lower() in ['true', '1', 't']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME','35ac86847482e9')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD','e4ff68eb89fada')
    REMEMBER_COOKIE_DURATION = 1800  # 30 minutes

    # app.config['MAIL_SERVER']='sandbox.smtp.mailtrap.io'
    # app.config['MAIL_PORT'] = 2525
    # app.config['MAIL_USERNAME'] = '35ac86847482e9'
    # app.config['MAIL_PASSWORD'] = '****fada'
    # app.config['MAIL_USE_TLS'] = True
    # app.config['MAIL_USE_SSL'] = False