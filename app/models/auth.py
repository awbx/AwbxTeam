from . import db
from datetime import datetime
from werkzeug.security import generate_password_hash,check_password_hash
from sqlalchemy import or_

class Follow(db.Model):
    __tablename__ = 'follows'
    follower_id = db.Column(db.Integer, db.ForeignKey('users.user_id'),primary_key=True)
    followed_id = db.Column(db.Integer, db.ForeignKey('users.user_id'),primary_key=True)

class Conversation(db.Model):
    __tablename__ = 'conversations'
    conv_id     = db.Column(db.Integer,autoincrement=True,primary_key=True)
    conv_user_x = db.Column(db.Integer,db.ForeignKey("users.user_id"))
    conv_user_y = db.Column(db.Integer,db.ForeignKey("users.user_id"))
    user_x      = db.relationship("User",foreign_keys=[conv_user_x],backref='user_x')
    user_y      = db.relationship("User",foreign_keys=[conv_user_y],backref='user_y')
    conv_timestamp      = db.Column(db.DateTime,default=datetime.utcnow)
    messages = db.relationship("Message",backref="conv",lazy='dynamic')

    def __init__(self,conv_user_x,conv_user_y):
        self.conv_user_x = conv_user_x
        self.conv_user_y = conv_user_y
    def get(self):
        return self.conv_id
    def other_user(self,user):
        if self.conv_user_x == user.user_id :
            return User.query.filter_by(user_id=self.conv_user_y).first()
        elif self.conv_user_y == user.user_id:
            return User.query.filter_by(user_id=self.conv_user_x).first()

    def save(self):
        db.session.add(self)
        self.update()
    def update(self):
        self.conv_timestamp = datetime.utcnow()
        db.session.commit()


class Message(db.Model):
    __tablename__ = "messages"
    msg_id  = db.Column(db.Integer,autoincrement=True,primary_key=True)
    msg_body = db.Column(db.Text,nullable=False)
    msg_sender = db.Column(db.Integer,db.ForeignKey("users.user_id"))
    msg_receiver = db.Column(db.Integer,db.ForeignKey("users.user_id"))
    msg_refer_conv = db.Column(db.Integer,db.ForeignKey("conversations.conv_id"))
    msg_timestamp = db.Column(db.DateTime,default=datetime.utcnow)

    def __init__(self,msg_body,msg_sender,msg_receiver,msg_refer_conv):
        self.msg_body = msg_body
        self.msg_sender = msg_sender
        self.msg_receiver = msg_receiver
        self.msg_refer_conv = msg_refer_conv
    def get(self):
        return self.msg_id
    def save(self):
        db.session.add(self)
        self.update()
    def update(self):
        db.session.commit()

class User(db.Model):
    __tablename__ = "users"

    user_id             = db.Column(db.Integer, primary_key=True,autoincrement=True)
    first_name          = db.Column(db.String(50),nullable=False)
    last_name           = db.Column(db.String(50),nullable=False)
    user_name           = db.Column(db.String(50),unique=True,nullable=False)
    user_mail           = db.Column(db.String(255),unique=True,nullable=False)
    user_pass           = db.Column(db.String(255),unique=True,nullable=False)
    user_timestamp      = db.Column(db.DateTime,default=datetime.now())
    mail_confirmed      = db.Column(db.Boolean,default=False)
    profession          = db.Column(db.String(300),default="Nothing !",)
    profile_url         = db.Column(db.Text,default=None)
    user_bio            = db.Column(db.Text,default="Hello, World!")
    posts               = db.relationship("Post",backref='user',lazy=True,cascade="all,delete")
    convs               = db.relationship("Conversation",backref=db.backref("user",lazy=True),primaryjoin="or_(Conversation.conv_user_x == User.user_id,Conversation.conv_user_y == User.user_id)",lazy="dynamic")
    followed = db.relationship('Follow',
                               foreign_keys=[Follow.follower_id],
                               backref=db.backref('follower', lazy='joined'),
                               lazy='dynamic',
                               cascade='all, delete-orphan')
    followers = db.relationship('Follow',
                                foreign_keys=[Follow.followed_id],
                                backref=db.backref('followed', lazy='joined'),
                                lazy='dynamic',
                                cascade='all, delete-orphan')

    def __init__(self,user_name,first_name,last_name,user_mail,user_pass):
        """ Initializing Info """ 
        self.user_name  = user_name
        self.first_name = first_name
        self.last_name  = last_name
        self.user_mail  = user_mail
        self.user_pass  = user_pass

    def get(self):
        return self.user_id

    def hash_password(self,method="sha512"):
        """ Encrypt the password """
        self.user_pass = generate_password_hash(self.user_pass,method=method)

    def check_password(self,password):
        """ Check password if correct """
        return check_password_hash(self.user_pass,password)

    def confirm_mail(self):
        """ Confirm mail """
        self.mail_confirmed = True
        db.session.commit()

    def follow(self, user):
        if not self.is_following(user):
            f = Follow(follower=self, followed=user)
            db.session.add(f)

    def unfollow(self, user):
        f = self.followed.filter_by(followed_id=user.user_id).first()
        if f:
            db.session.delete(f)

    def is_following(self, user):
        if user.user_id is None:
            return False
        return self.followed.filter_by(
            followed_id=user.user_id).first() is not None

    def is_followed_by(self, user):
        if user.user_id is None:
            return False
        return self.followers.filter_by(
            follower_id=user.user_id).first() is not None
    def we_ve_conv(self,user):
        return self.convs.filter(or_(Conversation.conv_user_x == user.user_id,Conversation.conv_user_y == user.user_id)).first() is  not None
    def get_conv(self,user):
        if self.we_ve_conv(user):
            return self.convs.filter(or_(Conversation.conv_user_x == user.user_id,Conversation.conv_user_y == user.user_id)).first()
    def add_conv(self,user):
        if not self.we_ve_conv(user):
            conv = Conversation(self.user_id,user.user_id)
            conv.save()
    def delete_selected_posts(self,posts_ids):
        for index in posts_ids:
            post = Post.query.get(index)
            if not post:return False
            post.post_removed = True
            self.update()
        return True

    def update(self):
        db.session.commit()
    def save(self):
        """ Save user to database """
        db.session.add(self)
        db.session.commit()

class Post(db.Model):
    __tablename__ = "posts"

    post_id         = db.Column(db.Integer,autoincrement=True,primary_key=True)
    post_title      = db.Column(db.String(300),nullable=False)
    post_body       = db.Column(db.Text,nullable=False)
    post_timestamp  = db.Column(db.DateTime,default=datetime.utcnow)
    post_comments   = db.relationship("Comment",backref="post",lazy=True)
    post_likes      = db.relationship("Like",backref="post",lazy=True) 
    post_author     = db.Column(db.Integer,db.ForeignKey("users.user_id"),nullable=False)
    post_removed    = db.Column(db.Boolean,default=False,nullable=False)

    def __init__(self,post_author,post_title,post_body):
        self.post_author    = post_author
        self.post_title     = post_title
        self.post_body      = post_body
    def get(self):
        return self.post_id
    def like_post(self,user):
        if not self.has_liked_post(user=user):
            like = Like(self.post_id,user.user_id)
            like.save()
    def unlike_post(self,user):
        if self.has_liked_post(user=user):
            Like.query.filter_by(post_liked_id=self.post_id,liker=user.user_id).delete()
            db.session.commit()

    def has_liked_post(self,user=None):
        return Like.query.filter(Like.post_liked_id.like(self.post_id),Like.liker.like(user.user_id)).count() > 0 
    
    def add_comment(self,user,body):
        """ Add Comments Function """
        comment = Comment(body,user.user_id,self.post_id)
        comment.save()

        
    def update(self):
        db.session.commit()
    def save(self):
        db.session.add(self)
        self.update()


class Comment(db.Model):
    __tablename__ = "comments"
    comment_id          = db.Column(db.Integer,autoincrement=True,primary_key=True)
    comment_body        = db.Column(db.Text,nullable=False)
    comment_timestamp   = db.Column(db.DateTime,default=datetime.utcnow)
    comment_author      = db.Column(db.Integer,db.ForeignKey("users.user_id"))
    comment_removed     = db.Column(db.Boolean,default=False)
    comment_post_id     = db.Column(db.Integer,db.ForeignKey("posts.post_id"))

    def __init__(self,comment_body,comment_author,comment_post_id):
        self.comment_body    = comment_body 
        self.comment_author  = comment_author
        self.comment_post_id = comment_post_id
    def get(self):
        return self.comment_id
    def update(self):
        db.session.commit()
    def save(self):
        """ Save Function """
        db.session.add(self)
        self.update()

class Like(db.Model):
    __tablename__ = "likes"
    like_id = db.Column(db.Integer,primary_key=True,autoincrement=True)
    post_liked_id = db.Column(db.Integer,db.ForeignKey("posts.post_id"),nullable=False)
    liker = db.Column(db.Integer,db.ForeignKey("users.user_id"),nullable=False)

    def __init__(self,post_liked_id,liker):
        self.post_liked_id = post_liked_id
        self.liker = liker
    def get(self):
        return self.like_id
    def update(self):
        """ Update Function """
        db.session.commit()
   
    def save(self):
        """ Save Function """
        db.session.add(self)
        db.session.commit()

