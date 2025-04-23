import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


from flask import Flask, jsonify, request 
from utils import save_audio_file
from model_runner import transcribe

app = Flask(__name__)


@app.route("/")
def hello():
    return "Hello, World!"



@app.route("/transcribe", methods=["POST"])
def transcribe_audio():
    print("🔹 Request received!")
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400
    
    file = request.files["audio"]
    model = request.form.get("model", "whisper")
    model_size = request.form.get("model_size", "base")
    
    try:
        file_bytes = file.read()
        saved_path = save_audio_file(file_bytes, extension="wav")
        
        result = transcribe(saved_path, model=model, model_size=model_size)
        return jsonify({"transcription":result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
        

if __name__ == "__main__":
    app.run(debug=True)