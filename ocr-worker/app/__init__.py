# ocr-worker/app/__init__.py
from flask import Flask
from dotenv import load_dotenv
import os

def create_app():
    load_dotenv()
    
    app = Flask(__name__)
    
    app.config['TESSERACT_PATH'] = os.getenv('TESSERACT_PATH', '/usr/bin/tesseract')
    app.config['TESSERACT_TEMP_DIR'] = os.getenv('TESSERACT_TEMP_DIR', '/tmp')

    from .routes import receipt as api_routes 
    app.register_blueprint(api_routes.bp)

    return app