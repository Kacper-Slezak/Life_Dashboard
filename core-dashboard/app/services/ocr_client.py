import requests
from fastapi import UploadFile, HTTPException


OCR_WORKER_URL = "http://ocr_worker:5000/process"

async def parse_receipt_via_ocr_worker(file: UploadFile):
    """
    Sending file to ocr_worker services and return JSON
    """
    file_contents = await file.read()

    files = {'file': (file.filename, file_contents, file.content_type)}

    try:
        response = requests.post(OCR_WORKER_URL, files=files)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error communicating with OCR worker: {e}")
        raise HTTPException(
            status_code=503, 
            detail=f"OCR services down. Error: {e}"
        )