"""
Main entry point for the Substation Operating Review Flask application.

This file creates the Flask app instance, loads configuration,
registers blueprints, and runs the development server.
"""

from flask import Flask
from routes.sos_routes import sos_bp
from routes.app_utils import get_config_database
import os
import secrets

# Create Flask application instance
app = Flask(__name__)

# Add secret key for session management
app.secret_key = secrets.token_hex(32)

db_path = get_config_database()

app.config['DATABASE'] = db_path

# Register the SOS blueprint containing all routes
app.register_blueprint(sos_bp)

# Run the Flask development server if this file is executed directly
if __name__ == "__main__":
    app.run(debug=True)
