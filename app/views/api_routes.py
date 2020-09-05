from flask import Blueprint, request, jsonify, url_for, render_template,abort,current_app
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask_socketio import send,emit
from flask_mail import Message as MESSAGE
from werkzeug.utils import secure_filename
from . import mail,socket
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
    verify_jwt_in_request,
    get_jwt_claims,
    view_decorators
)
from app.models.auth import User,Post,Comment,Like,Message,Conversation
from functools import wraps
from datetime import datetime
from PIL import Image
import time
import uuid
import io
import re
import os

api = Blueprint("api", __name__, url_prefix="/api/")

ts = URLSafeTimedSerializer(os.environ["FLASK_SECRET_KEY"])


USERNAME_PATTERN    = r"^[a-zA-Z0-9\_\-\.]{4,16}$"
EMAIL_PATTERN       = r"^([a-zA-Z0-9\_\-\.]{4,})\@([a-zA-Z]+)\.([a-zA_Z]{2,})$"
PASSWORD_PATTERN    = r"^[a-zA-Z0-9\s\_\-\.\@\&\<\>]{6,32}$"
NAME_PATTERN        = r"^[a-zA-Z\s\-]{,50}$"
TITLE_PATTERN       = r"[^\n]{4,300}"
BODY_PATTERN        = r"[^\n]{16,}"
COMMENT_PATTERN     = r"[^\n]+"
IMAGE_EXTENSIONS_ALLOWED = ['png','jpg','jpeg','gif']
IMAGE_SIZE          = (200,200)
USERS_ACTIVE = {}




def token_required(func):
    wraps(func)
    def wrapper(*args,**kwargs):
        verify_jwt_in_request()
        user_name = get_jwt_identity()
        current_user = User.query.filter_by(user_name=user_name).first()
        if not current_user:
            return jsonify(msg="Unauthorized !"),401
        
        return func(current_user,*args,**kwargs)
    wrapper.__name__ = func.__name__
    return wrapper


@api.route("/")
def main_api():
    """ Main API """
    return jsonify(msg="This an API")


@api.route("/login", methods=["POST"])
def login():
    """ Login Function """
    if request.method == "POST":
        if request.is_json:
            email = request.get_json().get("email", None)
            password = request.get_json().get("password", None)
            if not email:return jsonify(msg="Missing email !"),400
            elif not password:return jsonify(msg="Missing password !"),400
            else:
                if not re.match(EMAIL_PATTERN, email):return jsonify(msg="Please enter a valid email"), 400

                elif not re.match(PASSWORD_PATTERN, password):return jsonify(msg="Please enter a valid password"), 400
                else:
                    user = User.query.filter_by(user_mail=email).first()
                    if not user:return jsonify(msg="Email not registered yet !"), 404
                    elif not user.check_password(password):return jsonify(msg="Unauthorized !"), 401
                    elif not user.mail_confirmed:return jsonify(msg="This account not confirmed yet !", not_confirmed=True)
                    else:
                        resp = {"id": user.user_id, "first_name":user.first_name,"last_name":user.last_name,"username": user.user_name, "email": user.user_mail,"profession":user.profession}
                        access_token = create_access_token(identity=user.user_name)
                        current_app.logger.info("%s logged success",user.user_name)
                        return jsonify(msg="Login Succesfully", login=True,access_token=access_token,user=resp),200


        else:return jsonify(msg="Missing Data!")


@api.route("/register", methods=["POST", "GET"])
def register():
    """ Register Function """

    if request.method == "POST":
        if request.is_json:
            username = request.get_json().get("username", None)
            first_name = request.get_json().get("first_name", None)
            last_name = request.get_json().get("last_name", None)
            email = request.get_json().get("email", None)
            password = request.get_json().get("password", None)

            if not username:return jsonify(msg="Missing username !")
            elif not first_name:return jsonify(msg="Missing first name !")
            elif not last_name:return jsonify(msg="Missing last name !")
            elif not email:return jsonify(msg="Missing email !")
            elif not password:return jsonify(msg="Missing password !")
            else:
                if not re.match(USERNAME_PATTERN, username):return jsonify(msg="Please enter a valid username !"), 400
                elif not (
                    re.match(NAME_PATTERN, first_name)
                    or re.match(NAME_PATTERN, last_name)
                ):return jsonify(msg="Please enter a valid name"), 400
                elif not re.match(EMAIL_PATTERN, email):return jsonify(msg="Please enter a valid email"), 400
                elif not re.match(PASSWORD_PATTERN, password):return jsonify(msg="Please enter a valid password"), 400
                else:
                    if User.query.filter_by(user_mail=email).first():return jsonify(msg="E-Mail already taken !"), 409
                    elif User.query.filter_by(user_name=username).first():return jsonify(msg="Username already taken !"), 409
                    else:
                      
                        user = User(
                                username, first_name, last_name, email, password
                            )
                        user.hash_password()
                        user.save()
                        # Generate token to confime the account
                        fullname = f"{first_name.title()} {last_name.title()}"
                        send_mail_confirmation(email, fullname)
                        return jsonify(msg="Register Successfully !", success=True),201
                            
                    

        else:return jsonify(msg="Missing data !")
    else:return jsonify(msg="Method Not Allowed !"), 405


@api.route("/confirmed/<token>")
def confirm(token):
    """ Confirmation Route """

    try:
        email = ts.loads(token, salt="email_confirmation", max_age=100800)
        user = User.query.filter_by(user_mail=email).first()
        if not user:return jsonify(msg="Invalid token !"), 400
        elif user.mail_confirmed:return jsonify(msg="This account already confirmed !"), 200
        else:
            user.confirm_mail()
            return jsonify(msg="Email has been confirmed !"), 200
    except SignatureExpired:return jsonify(msg="Token has been expired !"), 440
    except BadSignature:return jsonify(msg="Invalid token !"), 400


@api.route("/re_confirm", methods=["POST", "GET"])
def re_confirm():
    """ Re-send Confirmation Message """

    if request.method == "POST":
        if request.is_json:
            email = request.get_json().get("email", None)
            if not email:return jsonify(msg="Missing email !")
            else:
                if not re.match(EMAIL_PATTERN, email):return jsonify(msg="Please enter a valid email !"),400
                else:
                    try :
                        user = User.query.filter_by(user_mail=email).first()
                        if not user:return jsonify(msg="This email not registered !"),404
                        elif user.mail_confirmed:return jsonify(msg="This account already confirmed !"),400
                        else:
                            fullname = f"{user.first_name.title()} {user.last_name.title()}"
                            send_mail_confirmation(user.user_mail,fullname)
                            return jsonify(msg="The confirmation mail has been sent !"),200
                    except Exception as e:
                        print(e)
                        return jsonify(msg="Something Wrong"),400
        else:
            return jsonify(msg="Missing Data !")
    else:
        return jsonify(msg="Method Not Allowed !"), 405


@api.route("/forgot_password", methods=["POST", "GET"])
def forgot_paasword():
    """ Forgot Password """

    if request.method == "POST":
        if request.is_json:
            email = request.get_json().get("email", None)
            if not email:
                return jsonify(msg="Missing email !")
            else:
                if not re.match(EMAIL_PATTERN, email):
                    return jsonify(msg="Please enter a valid email !"), 400
                else:
                    user = User.query.filter_by(user_mail=email).first()
                    if not user:
                        return jsonify(msg="This email not registered !"), 404
                    else:
                        fullname = f"{user.first_name.title()} {user.last_name.title()}"
                        send_reset_password(email,fullname)
                        return jsonify(msg="The email reset password has been sent !")

        else:
            return jsonify(msg="Missing Data !")
    else:
        return jsonify(msg="Method Not Allowed !"), 405


@api.route("/reset_password", methods=["POST", "GET"])
def reset_password():
    """ Reset Password """

    try:
        token = request.args.get("token",None)
       
        if token :
            email = ts.loads(token, salt="reset_password", max_age=3600)
            user = User.query.filter_by(user_mail=email).first()
            if not user:
                return jsonify(msg="Something Wrong !"), 404
            if request.method == "GET":
                # Redirect to reset password template
                return jsonify(msg="Token Valid" ,validToken=True),200
            elif request.method == "POST":
                if request.is_json:
                    new_pass = request.get_json().get("new_pass", None)
                    if not new_pass:
                        return jsonify(msg="Missing new password !"),400
                    else:
                        if not re.match(PASSWORD_PATTERN, new_pass):
                            return jsonify(msg="Please enter a valid new password"), 400
                        else:
                            user.user_pass = new_pass
                            user.hash_password()
                            user.update()
                            return jsonify(msg="Password has been changed !"), 200
                else:
                    return jsonify(msg="Missing Data !")
        else:
            return jsonify(msg="Missing token !"),400
    except SignatureExpired:
        return jsonify(msg="The token has been expired !"),440
    except BadSignature:
        return jsonify(msg="Invalid token !"),400
    


def send_mail_confirmation(email, name):

    token = ts.dumps(email, salt="email_confirmation")
    message = MESSAGE("Confirm Your Account")
    message.add_recipient(email)
    message.html = render_template(
        "confirm.html",
        product=os.environ["APP_NAME"],
        token_url="http://localhost:8080/#/confirmed?token=%s" % token,
        name=name,
    )
    mail.send(message)


def send_reset_password(email, name):
    token = ts.dumps(email, salt="reset_password")
    message = MESSAGE("Reset Your Account Password")
    message.add_recipient(email)
    message.html = render_template(
        "fpassword.html",
        product=os.environ["APP_NAME"],
        token_url= "http://localhost:8080/#/reset_password?token=%s" % token ,
        name=name,
    )
    mail.send(message)




@api.route("/profile")
@token_required
def my_profile(current_user):
    
    resp = {"id": current_user.user_id, "first_name":current_user.first_name.title(),"last_name":current_user.last_name.title(),"username": current_user.user_name, "email": current_user.user_mail,"profession":current_user.profession,"availability":current_user.user_timestamp,"profile_url":current_user.profile_url}
    return jsonify(user=resp,success=True), 200

@api.route("/profile/update",methods=["PUT"])
@token_required
def update_profile(current_user):
    if request.method == "PUT":
        if not request.is_json:abort(400)
        first_name  = request.get_json().get("first_name",None)
        last_name   = request.get_json().get("last_name",None)
        username    = request.get_json().get("username",None)
        email       = request.get_json().get("email",None)
        profession  = request.get_json().get("profession",None)
        # bio         = request.get_json().get("bio",None)
        if not first_name:return jsonify(msg="Missing first name !"),400
        elif not last_name:return jsonify(msg="Missing last name !"),400
        elif not username:return jsonify(msg="Missing username !"),400
        elif not email:return jsonify(msg="Missing email !"),400
        elif not profession:return jsonify(msg="Missing profession"),400
        # elif not bio:return jsonify(msg="Missing bio !"),400
        else:
            current_user.first_name = first_name
            current_user.last_name = last_name
            current_user.user_name = username
            current_user.user_mail = email
            current_user.profession = profession
            current_user.update()
            return jsonify(msg="Profile updated successfully !"),200


@api.route("/profile/<int:user_id>")
@token_required
def profile_info(current_user,user_id=None):
    user = User.query.filter_by(user_id=user_id).first()
    if not user:return abort(404)
    resp = {"is_followed_by_me":user.is_followed_by(current_user),"id": user.user_id, "first_name":user.first_name.title(),"last_name":user.last_name.title(),"username": user.user_name, "email": user.user_mail,"profession":user.profession,"availability":user.user_timestamp,"profile_url":user.profile_url}
    return jsonify(user=resp,success=True),200


@api.route("/posts")
@token_required
def get_posts(current_user):
    posts = []
    if len(current_user.posts) >0:
        posts = [dict(
            post_id=post.post_id,
            post_author=current_user.user_name,
            post_title=post.post_title,
            post_body=post.post_body,
            post_timestamp=post.post_timestamp,
            post_likes_length=len(post.post_likes),
            post_comments_length=len(post.post_comments),
            ) for post in current_user.posts if not post.post_removed]

    return jsonify(posts=posts)

@api.route("/posts/new",methods=["POST"])
@token_required
def new_post(current_user):
    if request.method == "POST":
        if request.is_json:
            post_title = request.get_json().get("post_title",None)
            post_body  = request.get_json().get("post_body",None)
            if not post_title:return jsonify(msg="Missing post title !"),400
            elif not post_body:return jsonify(msg="Missing post body !"),400
            else:
                if not re.match(TITLE_PATTERN,post_title):return jsonify(msg="Invalid post title !"),400
                elif not re.match(BODY_PATTERN,post_body):return jsonify(msg="Invalid post body"),400
                else:
                    post = Post(current_user.user_id,post_title,post_body)
                    post.save()
                    return jsonify(msg="Post added successfully !",success=True),200

@api.route("/posts/edit/<int:post_id>",methods=["PUT","GET"])
@token_required
def edit_post(current_user,post_id=None):
    """ Edit Post Function """
    post = Post.query.filter(Post.post_id.like(post_id)).filter(Post.post_removed.like(0)).first()
    if not post:return jsonify(msg="Post Not Found !"),404
    elif not current_user.user_id == post.user.user_id:return abort(403)
    if request.method == "PUT":
        if request.is_json:
            post_title = request.get_json().get("post_title",None)
            post_body = request.get_json().get("post_body",None)

            if not post_title:return jsonify(msg="Missing post title"),400
            elif not post_body:return jsonify(msg="Missing post body"),400
            else:
                if not re.match(TITLE_PATTERN,post_title):return jsonify(msg="Invalid post title")
                elif not re.match(BODY_PATTERN,post_body):return jsonify(msg="Invalid post body")
                else:
                    post.post_title = post_title
                    post.post_body  = post_body
                    post.update()
                    return jsonify(msg="Post updated successfully !",success=True),200
    elif request.method == "GET":
        resp = dict(
        post_id=post.post_id,
        post_author=post.user.user_name,
        full_name=f"{post.user.first_name.title()} {post.user.last_name.title()}",
        post_title=post.post_title,
        post_body=post.post_body,
        post_timestamp=post.post_timestamp
        )
        return jsonify(post=resp),200
   
@api.route("/posts/remove/<int:post_id>",methods=["DELETE"])
@token_required
def remove_post(current_user,post_id=None):
    if request.method == "DELETE":
        post = Post.query.filter(Post.post_id.like(post_id)).filter(Post.post_removed.like(0)).first()
        if not post:return jsonify(msg="Post not found !"),404
        elif not current_user.user_id == post.user.user_id:return abort(403)
        post.post_removed = True
        post.update()
        return jsonify(msg="Post removed successfully !",success=True),200


@api.route("/posts/remove_selected",methods=["POST"])
@token_required
def remove_selected(current_user):
    if request.method == "POST":
        if not request.is_json:abort(400)
        posts_ids = request.get_json().get("posts_ids",None)
        if not posts_ids:return jsonify(msg="Missing posts ids !"),400
        res = current_user.delete_selected_posts(posts_ids)
        if not res:return jsonify(msg="We can't remove unlocated posts"),404
        return jsonify(msg="Posts Selected Removed Successfully !"),200
@api.route("/posts/all")
@token_required
def all_posts(current_user):
    posts = Post.query.filter(Post.post_removed.like(0)).order_by(Post.post_timestamp.desc()).all()
    if len(posts) >0:
        resp = [dict(
            post_id=post.post_id,
            post_author=post.user.user_name,
            profile_url=post.user.profile_url,
            full_name=f"{post.user.first_name.title()} {post.user.last_name.title()}",
            post_title=post.post_title,
            post_body=post.post_body,
            post_timestamp=post.post_timestamp,
            post_liked=post.has_liked_post(current_user),
            post_likes_length=len(post.post_likes),
            post_comments_length=len(post.post_comments),
            is_show=False,
            comment_body="",
            user_id=post.user.user_id
            ) for post in posts if not post.post_removed]
    return jsonify(posts=resp,success=True) 

@api.route("/posts/view/<int:post_id>")
@token_required
def view_post(current_user,post_id):
    """ View Post Function """
    post = Post.query.filter(Post.post_id.like(post_id)).filter(Post.post_removed.like(0)).first()
    if not post:return jsonify(msg="Post Not Found !"),404
    resp = dict(
        post_id=post.post_id,
        post_author=post.user.user_name,
        full_name=f"{post.user.first_name.title()} {post.user.last_name.title()}",
        post_title=post.post_title,
        post_body=post.post_body,
        post_liked=post.has_liked_post(current_user),
        post_likes_length=len(post.post_likes),
        post_comments_length=len(post.post_comments),
        post_timestamp=post.post_timestamp,
        profile_url=post.user.profile_url,
        user_id=post.user.user_id,
        post_comments=[dict(
            comment_id=co.comment_id,
            comment_body=co.comment_body,
            comment_author=User.query.filter_by(user_id=co.comment_author).first().user_name,
            profile_url=User.query.filter_by(user_id=co.comment_author).first().profile_url,
            user_id=User.query.filter_by(user_id=co.comment_author).first().user_id,

            comment_timestamp = co.comment_timestamp
        ) for co in post.post_comments])
    return jsonify(post=resp),200


@api.route("/posts/like",methods=["POST"])
@token_required
def post_like(current_user):
    if request.method == "POST":
        if request.is_json:
            post_id = request.get_json().get("post_id",None)
            if not post_id:return jsonify(msg="Missing post id !")
            post = Post.query.filter(Post.post_id.like(post_id)).first()
            if not post:return jsonify(msg="Post not found !"),404
            elif post.has_liked_post(current_user):post.unlike_post(current_user)
            else:post.like_post(current_user)
            return jsonify(success=True),200
            
@api.route("/posts/add_comment",methods=["POST"])
@token_required
def add_comment(current_user):
    """ Add Comment Function """
    if request.method == "POST":
        if not request.is_json:abort(400)
        comment_body    = request.get_json().get("comment_body",None)
        post_id         = request.get_json().get("post_id",None)
        if not comment_body:return jsonify(msg="Missing comment body !"),400
        elif not post_id:return jsonify(msg="Missing post id"),400
        elif not re.match(COMMENT_PATTERN,comment_body):return jsonify(msg="Invalid comment body"),400
        else:
            post = Post.query.filter_by(post_id=post_id).first()
            if not post:
                return jsonify(msg="Post not found"),404
            post.add_comment(current_user,comment_body)
            return jsonify(msg="Comment added successfully !",success=True),200
@api.route("/follow",methods=["POST"])
@token_required
def follow(current_user):
    if request.method == "POST":
        user_id = request.get_json().get("user_id",None)
        if not user_id:return jsonify(msg="Missing user id"),400
        user = User.query.filter_by(user_id=user_id).first()
        if not user:return jsonify(msg="User not found !"),404
        if current_user.is_following(user):
            current_user.unfollow(user)
        else:
            current_user.follow(user)
        current_user.update()
        return jsonify(success=True),200

@api.route("/messages")
@token_required
def get_convs(current_user):
    resp = [dict(
        conv_id=conv.conv_id,
        conv_timestamp=conv.conv_timestamp,
        user_id=conv.other_user(current_user).user_id,
        profile_url=conv.other_user(current_user).profile_url,
        user_name=conv.other_user(current_user).user_name,
        last_msg=conv.messages.order_by(Message.msg_timestamp.desc()).first().msg_body if conv.messages.order_by(Message.msg_timestamp.desc()).first() else False

        ) for conv in current_user.convs.order_by(Conversation.conv_timestamp.desc()).all()]
    return jsonify(conversations=resp,success=True),200

@api.route("/messages/t/<int:conv_id>",methods=["POST","GET"])
@token_required
def add_message(current_user,conv_id=None):
    conv = Conversation.query.filter_by(conv_id=conv_id).first()
    if not conv:return jsonify(msg="Conversation not found"),404
    elif not(current_user.user_id == conv.conv_user_x or current_user.user_id == conv.conv_user_y):return abort(403)
    if request.method == "GET":
        resp = [dict(
            body=msg.msg_body,
            sender=msg.msg_sender,
            receiver=msg.msg_receiver,
            timestamp=msg.msg_timestamp,
            other_user=conv.other_user(current_user).user_id,
            profile_url=conv.other_user(current_user).profile_url
            ) for msg in conv.messages]
        return jsonify(messages=resp,success=True),200
    if request.method == "POST":
        if not request.is_json:return abort(400)
        msg_body     = request.get_json().get("msg_body",None)
        if not msg_body :return jsonify(msg="Missing msg body !"),400
        else:
            user = conv.other_user(current_user)
            msg = Message(msg_body,current_user.user_id,user.user_id,conv.conv_id)
            msg.save()
            conv.update()
            return jsonify(success=True),200



@socket.on("join")
@token_required
def join(current_user,payload):
    USERS_ACTIVE[payload['user_id']] = request.sid

@socket.on("message")
@token_required
def new_message(current_user,payload):
    send(payload,room=USERS_ACTIVE.get(payload['receiver'],None))

@socket.on("typing")
@token_required
def typing(current_user,payload):
    emit("typing",room=USERS_ACTIVE.get(payload['receiver'],None))


@api.route("/upload",methods=["POST"])
@token_required
def upload_profile_pic(current_user):
    if request.method == "POST":
        if request.files:
            picture = request.files.get("profile_pic",None)
            if not picture:return jsonify(msg="Missing profile pic"),400
            pic_filename = secure_filename(picture.filename)
            pic_extension = pic_filename.rsplit('.',1)[1]
           
            if pic_extension.lower() in IMAGE_EXTENSIONS_ALLOWED:
                try :
                    new_pic = Image.open(io.BytesIO(picture.read()))
                    new_pic.thumbnail(IMAGE_SIZE,Image.ANTIALIAS)
                    new_name = f"{uuid.uuid1().hex}.png"
                    new_pic.save(os.path.join(current_app.config["UPLOAD_FOLDER"],new_name),"PNG")
                    current_user.profile_url =url_for("upload_file",filename=new_name,_external=True)
                    current_user.update()
                except Exception as e:
                    print(e)
                    return jsonify(msg="Something Wrong !"),400

                else:
                    return jsonify(msg="Profile Picture Uploaded Successfully !",success=True,pic_url=url_for("upload_file",filename=new_name,_external=True)),200
            else:
                return jsonify(msg="We don't support these type of files !")

        else:
            return abort(400)
