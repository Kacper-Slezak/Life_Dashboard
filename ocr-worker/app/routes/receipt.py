import tempfile 
from flask import Blueprint,request, make_response, jsonify
import os
from app.services.ocr_services import run_ocr, parse_ocr


bp = Blueprint('api', __name__)

@bp.route('/process', methods=['POST'])
def process_receipt():
    if 'file' not in request.files:
        return make_response({'error': 'No file part in the request'}, 400)
    file = request.files['file']
    if file.filename == '':
        return make_response({'error': 'No selected file'}, 400)
    temp_fd, temp_path = tempfile.mkstemp(suffix=os.path.splitext(file.filename)[1])
    os.close(temp_fd)

    try:
        file.save(temp_path)
        
        raw_text = run_ocr(temp_path)
        
        if raw_text.startswith("ERROR"):
             return jsonify({'error': raw_text}), 500
        parsed_data = parse_ocr(raw_text)
        
        return jsonify({
            'status': 'success',
            'raw_text': raw_text,
            'parsed_data': parsed_data
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
        
    finally:

        if os.path.exists(temp_path):
            os.remove(temp_path)