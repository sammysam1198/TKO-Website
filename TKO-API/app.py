import os

from flask import Flask
from flask_cors import CORS

from db import init_db
from routes.core_routes import core_bp
from routes.subscriber_routes import subscriber_bp
from routes.post_routes import post_bp
from routes.auth_routes import auth_bp
from routes.dev_console_routes import dev_console_bp

app = Flask(__name__)
CORS(app)

app.register_blueprint(core_bp)
app.register_blueprint(subscriber_bp)
app.register_blueprint(post_bp)
app.register_blueprint(auth_bp)
app.register_blueprint(dev_console)

# Run table creation when the app starts on Render too
init_db()

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
