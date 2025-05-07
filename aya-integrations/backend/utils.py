import os
import uuid

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")

def ensure_upload_dir():
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)

def save_audio_file(file_data: bytes, extension="wav") -> str:
    """
    Save the incoming audio file to disk and return the file path. 
    
    parameters:
        file_data (bytes): Raw audio bytes
        extension (str): File extension  (wav, mp3)
    
    returns:
        str: Full path to the saved file
    """
    ensure_upload_dir()
    filename = f"{uuid.uuid4}.{extension}"
    file_path = os.path.join(UPLOAD_DIR, filename)
    
    with open(file_path, "wb") as f:
        f.write(file_data)
    
    return file_path