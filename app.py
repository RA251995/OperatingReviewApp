from flask import Flask
from routes.sos_routes import sos_bp

app = Flask(__name__)
app.config.from_pyfile('config.py') # Loads DATABASE path
app.register_blueprint(sos_bp)      # Registers routes

if __name__ == "__main__":
    app.run(debug=True)
