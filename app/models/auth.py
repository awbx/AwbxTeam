from . import db
from datetime import datetime
from werkzeug.security import generate_password_hash,check_password_hash



class User(db.Model):
    __tablename__ = "users"

    user_id     = db.Column(db.Integer, primary_key=True,autoincrement=True)
    user_name   = db.Column(db.String(50),unique=True,nullable=False)
    user_mail   = db.Column(db.String(255),unique=True,nullable=False)
    user_pass   = db.Column(db.String(255),unique=True,nullable=False)
    create_at   = db.Column(db.DateTime,default=datetime.now())
    mail_confirmed = db.Column(db.Boolean,default=False)

    def __init__(self,user_name,user_mail,user_pass):
        """ Initializing Info """ 
        self.user_name = user_name
        self.user_mail = user_mail
        self.user_pass = user_pass
    
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
    def update(self):
        db.session.commit()
    def save(self):
        """ Save user to database """
        db.session.add(self)
        db.session.commit()
        