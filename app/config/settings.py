import os
import datetime


class Config:
    SECRET_KEY                      = os.environ['FLASK_SECRET_KEY']
    PORT                            = os.environ['FLASK_DEBUG']
    DEBUG                           = False
    SQLALCHEMY_DATABASE_URI         = os.environ['DATABASE_URI']
    SQLALCHEMY_TRACK_MODIFICATIONS  = False
    MAIL_SERVER                     = "smtp.gmail.com"
    MAIL_PORT                       = 465
    MAIL_DEFAULT_SENDER             = (os.environ['APP_NAME'],os.environ['APP_MAIL_SENDER'])
    MAIL_USERNAME                   = os.environ['MAIL_USERNAME']
    MAIL_PASSWORD                   = os.environ['MAIL_PASSWORD']
    MAIL_USE_TLS                    = False
    MAIL_USE_SSL                    = True
    JWT_SECRET_KEY                  = "jwt-super_secret_key"
    JWT_ACCESS_TOKEN_EXPIRES        = datetime.timedelta(days=30)
    TEST_LOADING                    = False
    MAX_CONTENT_LENGTH              = 10000000

class development(Config):
    ENV = "development"
    DEBUG = True

class production(Config):
    ENV = "production"
    PORT = 8080