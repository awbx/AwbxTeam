from flask import Flask,jsonify
from flask_jwt_extended import JWTManager
from flask_mail import Mail
from flask_migrate import Migrate
from flask_cors import CORS
from flask_socketio import SocketIO
from .models import db
from .views.api_routes import api
from .views import mail,socket
from dotenv import load_dotenv
import time
import os


APP_DIR = os.path.dirname(__file__)
UPLOAD_FOLDER = os.path.join(APP_DIR,"../upload")

load_dotenv(os.path.join(APP_DIR, "../.env"))

# JWT extension
jwt = JWTManager()

# Migrate extension
migrate = Migrate()

# CORS extension
cors = CORS()#resources={r"/api/*": {"origins": "*"}})

def create_app():
    app = Flask(__name__)

    # Configuration

    app.config.from_object("app.config.settings." + os.environ["FLASK_ENV"])
    app.config["APP_DIR"] = APP_DIR
    app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

    # Initialize Extensions
    db.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app)
    socket.init_app(app)
    # Register Blueprints
    app.register_blueprint(api)

    with app.app_context():
        db.create_all()
    
    @app.errorhandler(404)
    def not_found(error):
        """ Not Found Function """
        return jsonify(msg="Content Not Found !"),error.code
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        """ Method Not Allowed """
        return jsonify(msg="Method Not Allowed !"),error.code
    
    @app.errorhandler(403)
    def forbidden(error):
        """ Forbidden Function """
        return jsonify(msg="You Don't Have Permission !"),error.code
    @app.errorhandler(400)
    def forbidden(error):
        """ 400 Function """
        return jsonify(msg="Missing Data Or Invalid Data !"),error.code
    @app.errorhandler(413)
    def forbidden(error):
        """ 413 Function """
        return jsonify(msg="This file too large!"),error.code
    
    @app.before_request
    def before_request():
        if app.config["TEST_LOADING"]:
            time.sleep(1)
  


    return app,socket
