import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


from flask import Flask, jsonify, request, send_file
from utils import save_audio_file, save_waveform
from model_runner import transcribe,load_model_and_tokenizer, synthesize_speech

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
        
@app.route("/synthesize", methods=["POST"])
def synthesize():
    tokenizer, model = load_model_and_tokenizer()
    data = request.json
    text = data.get("text", "").strip()

    if not text:
        return jsonify({"error": "Text input is required"}), 400
    waveform = synthesize_speech(text, tokenizer, model)
    audio_path = save_waveform(waveform)
    return send_file(audio_path, mimetype="audio/wav", as_attachment=True, download_name="output.wav")



if __name__ == "__main__":
    app.run(debug=True)