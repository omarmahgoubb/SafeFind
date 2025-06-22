from flask import Flask
from controllers.auth_controller import auth_bp
from controllers.posts_controller import posts_bp 
from controllers.admin_controller import admin_bp


def create_app():
    app = Flask(__name__)
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(posts_bp,  url_prefix="/api") 
# admin_controller.py
    app.register_blueprint(admin_bp, url_prefix="/api/admin")   # ← add this


    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)