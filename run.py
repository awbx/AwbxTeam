from app import create_app
from werkzeug.middleware.shared_data import SharedDataMiddleware
from flask_script import Manager
from flask_migrate import MigrateCommand



app,sccket = create_app()

manager = Manager(app)
manager.add_command('db', MigrateCommand)


#Share Upload folder
app.add_url_rule("/upload/<filename>","upload_file",build_only=True)
app.wsgi_app = SharedDataMiddleware(app.wsgi_app,{"/upload":app.config['UPLOAD_FOLDER']})


if __name__ == "__main__":
    manager.run()
    socket.run(app)