from flask import Flask
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from .models import db
from .views.api_routes import api
from .views import mail
from dotenv import load_dotenv
import os


APP_DIR = os.path.dirname(__file__)

load_dotenv(os.path.join(APP_DIR,"../.env"))

# JWT extension
jwt = JWTManager()

def create_app():
    app = Flask(__name__)

    #Configuration

    app.config.from_object("app.config.settings." +os.environ['FLASK_ENV'] )

    #Initialize Extensions
    db.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)

    #Register Blueprints
    app.register_blueprint(api)

    with app.app_context():
        db.create_all()

    return app