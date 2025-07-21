"""
Main entry point for the Substation Operating Review Flask application.

This file creates the Flask app instance, loads configuration,
registers blueprints, and runs the development server.
"""

from flask import Flask
from routes.sos_routes import sos_bp

# Create Flask application instance
app = Flask(__name__)

# Load configuration from config.py (e.g., DATABASE path)
app.config.from_pyfile('config.py')

# Register the SOS blueprint containing all routes
app.register_blueprint(sos_bp)

# Run the Flask development server if this file is executed directly
if __name__ == "__main__":
    app.run(debug=True)
