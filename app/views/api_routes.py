from flask import Blueprint,request,jsonify,url_for,render_template,redirect
from itsdangerous import URLSafeTimedSerializer,SignatureExpired,BadSignature
from flask_jwt_extended import create_access_token,jwt_required,get_jwt_identity,set_access_cookies,unset_access_cookies,jwt_optional
from flask_mail import Message
from . import mail
from app.models.auth import User
import re
import os


api = Blueprint('api',__name__,url_prefix="/api/")

ts = URLSafeTimedSerializer(os.environ['FLASK_SECRET_KEY'])


USERNAME_PATTERN    = r"^[a-zA-Z0-9\_\-\.]{4,16}$"
EMAIL_PATTERN       = r"^([a-zA-Z0-9\_\-\.]{4,})\@([a-zA-Z]+)\.([a-zA_Z]{2,})$"
PASSWORD_PATTERN    = r"^[a-zA-Z0-9\s\_\-\.\@\&\<\>]{6,32}$"


@api.route("/")
def main_api():
    """ Main API """
    return jsonify(msg="This an API")


@api.route("/login",methods=["POST","GET"])
@jwt_optional
def login():
    """ Login Function """
    if get_jwt_identity():
        return redirect(url_for("api.register"))
    if request.method == "POST":
        if request.is_json:
            username = request.get_json().get("username",None)
            password = request.get_json().get("password",None)
            if not username:
                return jsonify(msg="Missing username !")
            elif not password:
                return jsonify(msg="Missing password !")
            else:
                if not re.match(USERNAME_PATTERN,username):
                    return jsonify(msg="Please enter a valid username"),400
                elif not re.match(PASSWORD_PATTERN,password):
                    return jsonify(msg="Please enter a valid password"),400
                else:
                    user = User.query.filter_by(user_name=username).first()
                    if not user:
                        return jsonify(msg="Username not registered yet !"),404
                    elif not user.check_password(password):
                        return jsonify(msg="Unauthorized !"),401
                    elif not user.mail_confirmed:
                        return jsonify(msg="This account not confirmed yet !")
                    else:
                        access_token = create_access_token(identity=user.user_name)
                        resp = jsonify(msg="Login Succesfully")
                        set_access_cookies(resp,access_token)
                        return resp,200

        else:
            return jsonify(msg="Missing Data!")
    else:
        return jsonify(msg="Method Not Allowed !")

    

@api.route("/register",methods=["POST","GET"])
@jwt_optional
def register():
    """ Register Function """
    if get_jwt_identity():
        return redirect(url_for("api.register"))
    if request.method == "POST":
        if request.is_json:
            username = request.get_json().get("username",None)
            email    = request.get_json().get("email",None)
            password = request.get_json().get("password",None)
        
            if not username:
                return jsonify(msg="Missing username !")
            elif not email:
                return jsonify(msg="Missing email !")
            elif not password:
                return jsonify(msg="Missing password !")
            else:
                if not re.match(USERNAME_PATTERN,username):
                    return jsonify(msg="Please enter a valid username !"),400
                elif not re.match(EMAIL_PATTERN,email):
                    return jsonify(msg="Please enter a valid email"),400
                elif not re.match(PASSWORD_PATTERN,password):
                    return jsonify(msg="Please enter a valid password"),400
                else:
                    if User.query.filter_by(user_name=username).first():
                        return jsonify(msg="Username already taken !"),409
                    elif User.query.filter_by(user_mail=email).first():
                        return jsonify(msg="Email already taken !"),409
                    else:
                        try :
                            user = User(username,email,password)
                            user.hash_password()
                            user.save()
                            #Generate token to confime the account
                            send_mail_confirmation(email)
                            return jsonify(msg="Register Successfully !"),201
                        except Exception as e:
                            print(e)
                            return jsonify(msg="Something wrong !")

        else:
            return jsonify(msg="Missing data !")
    else:
        return jsonify(msg="Method Not Allowed !"),405
@api.route("/confirm/<token>")
@jwt_optional
def confirm(token):
    """ Confirmation Route """
    if get_jwt_identity():
        return redirect(url_for("api.register"))
    try:
        email = ts.loads(token,salt="email_confirmation",max_age=100800)
        user = User.query.filter_by(user_mail=email).first()
        if not user:
            return jsonify(msg="Invalid token !"),400
        elif user.mail_confirmed:
            return jsonify(msg="This account already confirmed !"),200
        else:
            user.confirm_mail()
            return jsonify(msg="Email has been confirmed !"),200
    except SignatureExpired:
        return jsonify(msg="Token has been expired !"),440
    except BadSignature :
            return jsonify(msg="Invalid token !"),400

@api.route("/re_confirm",methods=["POST","GET"])
@jwt_optional
def re_confirm():
    """ Re-send Confirmation Message """
    if get_jwt_identity():
        return redirect(url_for("api.register"))
    if request.method == "POST":
        if request.is_json:
            email = request.get_json().get("email",None)
            if not email:
                return jsonify(msg="Missing email !")
            else:
                if not re.match(EMAIL_PATTERN,email):
                    return jsonify(msg="Please enter a valid email !")
                else:
                    user = User.query.filter_by(user_mail=email).first()
                    if not user:
                        return jsonify(msg="This email not registered !")
                    elif user.mail_confirmed:
                        return jsonify(msg="This account already confirmed !")
                    else:
                        send_mail_confirmation(email)
                        return jsonify(msg="The confirmation mail has been sent !")
        else:
            return jsonify(msg="Missing Data !")
    else:
        return jsonify(msg="Method Not Allowed !"),405

@api.route("/forget_paasword",methods=["POST","GET"])
@jwt_optional
def forget_paasword():
    """ Forget Password """
    if get_jwt_identity():
        return redirect(url_for("api.register"))
    if request.method == "POST":
        if request.is_json:
            email = request.get_json().get("email",None)
            if not email:
                return jsonify(msg="Missing email !")
            else:
                if not re.match(EMAIL_PATTERN,email):
                    return jsonify(msg="Please enter a valid email !"),400
                else:
                    user = User.query.filter_by(user_mail=email).first()
                    if not user:
                        return jsonify(msg="This email not registered !"),404
                    else:
                        send_reset_password(email)
                        return jsonify(msg="The email reset password has been sent !")

        else:
            return jsonify(msg="Missing Data !")
    else:
        return jsonify(msg="Method Not Allowed !"),405

@api.route("/reset_password/<token>",methods=["POST","GET"])
@jwt_optional
def reset_password(token):
    """ Reset Password """
    if get_jwt_identity():
        return redirect(url_for("api.register"))
    try :
        email = ts.loads(token,salt="reset_password",max_age=3600)
        user = User.query.filter_by(user_mail=email).first()
        if not user:
            return jsonify(msg="Something Wrong !"),404
        if request.method == "GET":
            #Redirect to reset password template
            return jsonify(msg="Reset password template will be shown here !")
        elif request.method == "POST":
            if request.is_json:
                new_pass = request.get_json().get("new_pass",None)
                if not new_pass :
                    return jsonify(msg="Missing new password !")
                else:
                    if not re.match(PASSWORD_PATTERN,new_pass):
                        return jsonify(msg="Please enter a valid new password"),400
                    else:
                        user.user_pass = new_pass
                        user.hash_password()
                        user.update()
                        return jsonify(msg="Password has been changed !"),200
            else:
                return jsonify(msg="Missing Data !")
    except BadSignature:
        return jsonify(msg="Invalid token !")
    except SignatureExpired:
        return jsonify(msg="The token has been expired !")
    

def send_mail_confirmation(email,name="test"):
    
    token = ts.dumps(email,salt="email_confirmation")
    message = Message("Confirma Your Account")
    message.add_recipient(email)
    message.html = render_template("confirm.html",product=os.environ["APP_NAME"],token_url=url_for("api.confirm",token=token,_external=True),name=name)
    mail.send(message)

def send_reset_password(email,name="test"):
    token = ts.dumps(email,salt="reset_password")
    message = Message("Reset Your Account Password")
    message.add_recipient(email)
    message.html = render_template("fpassword.html",product=os.environ["APP_NAME"],token_url=url_for("api.reset_password",token=token,_external=True),name=name)
    mail.send(message)



@api.route("/logout",methods=["POST"])
@jwt_required
def logout():
    resp = jsonify(msg="Logout Succesfully !")
    unset_access_cookies(resp)
    return resp,200


@api.route("/profile")
@jwt_required
def my_profile():
    username = get_jwt_identity()
    user = User.query.filter_by(user_name=username).first()
    if not username:
        return jsonify(msg="Something wrong !"),403
    resp = {
        "id":user.user_id,
        "username":user.user_name,
        "email":user.user_mail
    }
    return jsonify(resp),200