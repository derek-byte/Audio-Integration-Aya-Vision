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


def save_waveform(waveform, sample_rate=16000, output_dir="generated_audios"):
    import torchaudio
    os.makedirs(output_dir, exist_ok=True)
    audio_id = str(uuid.uuid4())
    audio_path = os.path.abspath(os.path.join(output_dir, f"{audio_id}.wav"))
    torchaudio.save(audio_path, waveform, sample_rate)
    return audio_path
