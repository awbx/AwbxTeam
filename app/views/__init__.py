from flask_mail import Mail

from flask_socketio import SocketIO


#Initialize Mail 

mail = Mail()
socket = SocketIO(cors_allowed_origins="*")

