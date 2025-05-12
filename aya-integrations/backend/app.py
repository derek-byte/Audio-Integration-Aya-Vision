from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from flask_sock import Sock
import base64
import io
import os
import tempfile
import uuid
import logging
import json
import time
import torch
import torchaudio
import numpy as np
import threading
import struct
import requests
from faster_whisper import WhisperModel
from dotenv import load_dotenv
from gtts import gTTS  # Google Text-to-Speech

load_dotenv()

# Load environment variables for Cohere API
COHERE_API_KEY = os.getenv("COHERE_API_KEY")

app = Flask(__name__)
CORS(app, resources={
    r"/*": {"origins": ["http://localhost:3000"]}
})  # Enable CORS for all routes
sock = Sock(app)
logging.basicConfig(level=logging.INFO)

# Initialize models - lazy loading for efficiency
models = {
    "faster_whisper": None,
    "whisper": None,
    "wav2vec2": None,
    "nemo": None,
    "seamless": None
}

# Default model to use
DEFAULT_MODEL = "faster_whisper"
CURRENT_MODEL = DEFAULT_MODEL

# Default TTS model
DEFAULT_TTS_MODEL = "gtts"
CURRENT_TTS_MODEL = DEFAULT_TTS_MODEL

# Available TTS models
TTS_MODELS = ["gtts", "groqtts", "groqasr"]

# Store active sessions
active_sessions = {}

class AudioBuffer:
    def __init__(self, sample_rate=16000):
        self.buffer = np.array([], dtype=np.float32)
        self.sample_rate = sample_rate
        self.lock = threading.Lock()
    
    def add_audio(self, audio_bytes):
        with self.lock:
            try:
                # Use little-endian int16, which is what the client sends
                audio_np = np.frombuffer(audio_bytes, dtype='<i2').astype(np.float32) / 32768.0
                self.buffer = np.concatenate((self.buffer, audio_np))
                logging.debug(f"Added {len(audio_np)} samples to buffer")
            except Exception as e:
                logging.error(f"Failed to decode audio bytes: {e}")
    
    def get_audio(self, clear=True):
        with self.lock:
            audio = self.buffer.copy()
            if clear:
                self.buffer = np.array([], dtype=np.float32)
            return audio
    
    def get_length_seconds(self):
        with self.lock:
            return len(self.buffer) / self.sample_rate

def load_model(model_name, model_size=None):
    """
    Lazy load the specified model
    """
    if model_name not in models:
        raise ValueError(f"Unknown model: {model_name}")
        
    if models[model_name] is not None:
        return models[model_name]
        
    if model_name == "faster_whisper":
        size = model_size or "base"
        logging.info(f"Loading faster-whisper model: {size}")
        models[model_name] = WhisperModel(size, device="cpu")  # Use "cuda" if you have a compatible GPU
    
    elif model_name == "whisper":
        import whisper
        size = model_size or "base"
        logging.info(f"Loading whisper model: {size}")
        models[model_name] = whisper.load_model(size)
    
    elif model_name == "wav2vec2":
        from transformers import Wav2Vec2ForCTC, Wav2Vec2Tokenizer
        model_id = model_size or "facebook/wav2vec2-base-960h"
        logging.info(f"Loading wav2vec2 model: {model_id}")
        tokenizer = Wav2Vec2Tokenizer.from_pretrained(model_id)
        model = Wav2Vec2ForCTC.from_pretrained(model_id)
        models[model_name] = {"model": model, "tokenizer": tokenizer}
    
    elif model_name == "nemo":
        from nemo.collections.asr.models import ASRModel
        model_id = model_size or "stt_en_conformer_ctc_small"
        logging.info(f"Loading NeMo model: {model_id}")
        models[model_name] = ASRModel.from_pretrained(model_name=model_id)
    
    elif model_name == "seamless":
        from models.seamless_inference import get_seamless_default_config, load_model as load_seamless_model
        logging.info("Loading Seamless model")
        models[model_name] = load_seamless_model(model_config=get_seamless_default_config())
    
    
    return models[model_name]

@app.route('/set-model', methods=['POST'])
def set_model():
    """
    Endpoint to set the active transcription model
    """
    data = request.json
    model_name = data.get('model', DEFAULT_MODEL)
    model_size = data.get('size')
    
    global CURRENT_MODEL
    
    try:
        if model_name not in models:
            return jsonify({'error': f'Unknown model: {model_name}'}), 400
            
        # Load the model if not already loaded
        load_model(model_name, model_size)
        CURRENT_MODEL = model_name
        
        return jsonify({
            'success': True,
            'message': f'Model set to {model_name}',
            'model': model_name
        })
    except Exception as e:
        logging.error(f"Error setting model: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/available-models', methods=['GET'])
def get_available_models():
    """
    Return the list of available transcription models
    """
    return jsonify({
        'models': list(models.keys()),
        'current_model': CURRENT_MODEL
    })

@app.route('/available-tts-models', methods=['GET'])
def get_available_tts_models():
    """
    Return the list of available text-to-speech models
    """
    return jsonify({
        'models': TTS_MODELS,
        'current_model': CURRENT_TTS_MODEL
    })

@app.route('/set-tts-model', methods=['POST'])
def set_tts_model():
    """
    Endpoint to set the active text-to-speech model
    """
    data = request.json
    model_name = data.get('model', DEFAULT_TTS_MODEL)
    
    global CURRENT_TTS_MODEL
    
    try:
        if model_name not in TTS_MODELS:
            return jsonify({'error': f'Unknown TTS model: {model_name}'}), 400
            
        CURRENT_TTS_MODEL = model_name
        
        return jsonify({
            'success': True,
            'message': f'TTS model set to {model_name}',
            'model': model_name
        })
    except Exception as e:
        logging.error(f"Error setting TTS model: {str(e)}")
        return jsonify({'error': str(e)}), 500

@sock.route('/stream-audio')
def stream_audio(ws):
    """
    WebSocket endpoint that receives audio chunks and returns transcriptions
    """
    logging.info("WebSocket connection established")
    
    # Create a unique session ID for this connection
    session_id = str(uuid.uuid4())
    active_sessions[session_id] = AudioBuffer()
    
    try:
        while True:
            data = ws.receive()
            if not data:
                continue
                
            try:
                json_data = json.loads(data)
                audio_data = json_data.get('audio_data')
                model_name = json_data.get('model', CURRENT_MODEL)
                
                if audio_data:
                    # Decode base64 audio data
                    audio_bytes = base64.b64decode(audio_data)
                    
                    # Process with selected STT model
                    transcription = process_audio(audio_bytes, session_id, model_name)
                    
                    # Only send back if there's actual transcription
                    if transcription:
                        ws.send(json.dumps({
                            'transcription': transcription,
                            'timestamp': time.time(),
                            'model': model_name
                        }))
            except Exception as e:
                logging.error(f"Error processing audio chunk: {str(e)}")
                ws.send(json.dumps({
                    'error': str(e)
                }))
    except Exception as e:
        logging.error(f"WebSocket error: {str(e)}")
    finally:
        # Clean up session
        if session_id in active_sessions:
            del active_sessions[session_id]

@app.route('/transcribe', methods=['POST'])
def transcribe():
    """
    HTTP endpoint for full audio file transcription (alternative to WebSocket)
    """
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file provided'}), 400
        
    audio_file = request.files['audio']
    model_name = request.form.get('model', CURRENT_MODEL)
    model_size = request.form.get('size')
    
    # Create a temporary file
    temp_file_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.webm")
    audio_file.save(temp_file_path)
    
    try:
        # Process with the selected STT model
        transcription = process_audio_file(temp_file_path, model_name, model_size)
        return jsonify({
            'transcription': transcription,
            'model': model_name
        })
    except Exception as e:
        logging.error(f"Error transcribing audio: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        # Clean up temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


def synthesize_speech(text, lang='en', slow=False, model=None):
    """
    Convert text to speech using the specified TTS model
    
    Args:
        text (str): Text to synthesize
        lang (str): Language code for synthesis
        slow (bool): Whether to use slower speech rate
        model (str): TTS model to use (defaults to current model)
    
    Returns:
        str: Path to the generated audio file
    """
    if model is None:
        model = CURRENT_TTS_MODEL
        
    try:
        # Create a temporary file
        temp_dir = tempfile.gettempdir()
        audio_path = os.path.join(temp_dir, f"{uuid.uuid4()}.mp3")
        
        if model == "gtts":
            # Generate speech using gTTS
            tts = gTTS(text=text, lang=lang, slow=slow)
            tts.save(audio_path)
        elif model == "groqtts":
            # Use Groq TTS model
            import model_runner
            model_runner.synthesize_speech(text, "groqtts", output_filename=audio_path)
        else:
            # Default to gTTS if model is not recognized
            logging.warning(f"Unknown TTS model: {model}, falling back to gtts")
            tts = gTTS(text=text, lang=lang, slow=slow)
            tts.save(audio_path)
            
        return audio_path
    except Exception as e:
        logging.error(f"Error in synthesize_speech: {str(e)}")
        raise


@app.route('/synthesize', methods=['POST'])
def synthesize():
    """
    Endpoint to synthesize speech from text
    """
    data = request.json
    text = data.get("text", "").strip()
    lang = data.get("lang", "en")
    slow = data.get("slow", False)
    model = data.get("model", CURRENT_TTS_MODEL)

    if not text:
        return jsonify({"error": "Text input is required"}), 400
    
    try:
        audio_path = synthesize_speech(text, lang, slow, model)
        return send_file(audio_path, mimetype="audio/mp3", as_attachment=True, download_name="output.mp3")
    except Exception as e:
        logging.error(f"Error synthesizing speech: {str(e)}")
        return jsonify({"error": str(e)}), 500
    

# Serve generated audio files
@app.route('/audio/<filename>', methods=['GET'])
def serve_audio(filename):
    """
    Serve generated audio files
    """
    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, filename)
    
    # Check if the file exists and its extension
    if os.path.exists(file_path):
        if file_path.endswith('.mp3'):
            mimetype = "audio/mp3"
        else:
            mimetype = "audio/wav"
        return send_file(file_path, mimetype=mimetype)
    else:
        return jsonify({"error": "File not found"}), 404


@app.route('/aya-response', methods=['POST'])
def get_aya_response():
    """
    Endpoint to send transcribed text and optional image to Cohere's Aya Vision API and return the response
    """
    if not COHERE_API_KEY:
        return jsonify({'error': 'COHERE_API_KEY not configured'}), 500

    try:
        data = request.json
        if not data or 'message' not in data:
            return jsonify({'error': 'No message provided'}), 400

        user_message = data['message']
        image_data = data.get('image')  # Optional base64 JPEG image

        # Build the message content list
        content = [{"type": "text", "text": user_message}]
        if image_data:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{image_data}"
                }
            })

        # Construct the request payload
        payload = {
            "model": "c4ai-aya-vision-32b",
            "messages": [
                {
                    "role": "user",
                    "content": content
                }
            ]
        }

        headers = {
            "Authorization": f"Bearer {COHERE_API_KEY}",
            "Content-Type": "application/json"
        }

        response = requests.post(
            "https://api.cohere.ai/v2/chat",
            headers=headers,
            json=payload
        )

        response.raise_for_status()
        result = response.json()

        # Extract text response from result
        text_response = ""
        if "text" in result:
            text_response = result["text"]
        elif "message" in result and "content" in result["message"]:
            for item in result["message"]["content"]:
                if item.get("type") == "text":
                    text_response += item.get("text", "")

        return jsonify({
            'response': text_response,
            'message_id': result.get('message_id', '')
        })

    except requests.exceptions.RequestException as e:
        logging.error(f"Error calling Cohere API: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            logging.error(f"Response: {e.response.text}")
        return jsonify({'error': f'Error from Cohere API: {str(e)}'}), 500
    except Exception as e:
        logging.error(f"Error in get_aya_response: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/aya-response-tts', methods=['POST'])
def get_aya_response_with_tts():
    """
    Enhanced endpoint that returns both Aya Vision response and synthesized speech
    """
    if not COHERE_API_KEY:
        return jsonify({'error': 'COHERE_API_KEY not configured'}), 500

    try:
        data = request.json
        if not data or 'message' not in data:
            return jsonify({'error': 'No message provided'}), 400

        user_message = data['message']
        image_data = data.get('image')
        chat_history = data.get('chatHistory', [])
        tts_model = data.get('tts_model', CURRENT_TTS_MODEL)  # Get the specified TTS model

        # Format chat history into Cohere's message format
        messages = format_chat_history(chat_history)
        # Append current user message and optional image
        content = [{"type": "text", "text": user_message}]
        if image_data:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{image_data}"
                }
            })
        messages.append({
            "role": "user",
            "content": content
        })

        payload = {
            "model": "c4ai-aya-vision-32b",
            "messages": messages
        }

        headers = {
            "Authorization": f"Bearer {COHERE_API_KEY}",
            "Content-Type": "application/json"
        }

        response = requests.post(
            "https://api.cohere.ai/v2/chat",
            headers=headers,
            json=payload
        )

        response.raise_for_status()
        result = response.json()

        # Extract response text
        text_response = ""
        if "text" in result:
            text_response = result["text"]
        elif "message" in result and "content" in result["message"]:
            for item in result["message"]["content"]:
                if item.get("type") == "text":
                    text_response += item.get("text", "")

        # Generate audio using the specified TTS model
        audio_path = synthesize_speech(text_response, model=tts_model)
        audio_url = f"http://localhost:5000/audio/{os.path.basename(audio_path)}"

        return jsonify({
            'response': text_response,
            'message_id': result.get('message_id', ''),
            'audio_url': audio_url
        })

    except requests.exceptions.RequestException as e:
        logging.error(f"Error calling Cohere API: {str(e)}")
        if hasattr(e, 'response') and e.response is not None:
            logging.error(f"Response: {e.response.text}")
        return jsonify({'error': f'Error from Cohere API: {str(e)}'}), 500
    except Exception as e:
        logging.error(f"Error in get_aya_response_with_tts: {str(e)}")
        return jsonify({'error': str(e)}), 500


def format_chat_history(chat_history):
    """
    Format raw chat history into list of message dicts for Cohere's /v2/chat endpoint.
    Expects input as: [{"role": "user"/"assistant", "message": "text"}]
    """
    formatted = []
    for item in chat_history:
        role = item.get("role")
        message_text = item.get("message")
        if role and message_text:
            formatted.append({
                "role": role,
                "content": [{"type": "text", "text": message_text}]
            })
    return formatted


def process_audio(audio_bytes, session_id, model_name=CURRENT_MODEL):
    """
    Process audio bytes with the selected STT model
    For streaming, we accumulate chunks and process when enough data is available
    """
    buffer = active_sessions.get(session_id)
    if not buffer:
        logging.error(f"Session {session_id} not found")
        return "Error: Session not found"
    
    try:
        # Add the new audio to the buffer
        buffer.add_audio(audio_bytes)
    except Exception as e:
        logging.error(f"Error adding audio to buffer: {str(e)}")
        return ""
    
    # Check if we have enough audio to process (at least 1 second)
    if buffer.get_length_seconds() < 1.0:
        return ""  # Not enough audio yet
    
    # Get audio from buffer and process
    audio_np = buffer.get_audio()
    
    try:
        # Make sure the audio is not empty after getting from buffer
        if len(audio_np) == 0:
            return ""
            
        # Apply preprocessing for noise reduction if needed
        cleaned_audio = audio_np
        
        # Save as temporary file for models to process
        temp_file_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.wav")
        
        # Ensure audio is in correct format for saving
        audio_tensor = torch.tensor(cleaned_audio).unsqueeze(0)
        if torch.isnan(audio_tensor).any() or torch.isinf(audio_tensor).any():
            logging.warning("Audio contains NaN or Inf values, replacing with zeros")
            audio_tensor = torch.nan_to_num(audio_tensor, nan=0.0, posinf=0.0, neginf=0.0)
            
        # Normalize audio to prevent clipping
        if audio_tensor.abs().max() > 1.0:
            audio_tensor = audio_tensor / audio_tensor.abs().max()
            
        torchaudio.save(temp_file_path, audio_tensor, 16000)
        
        # Process with the selected model
        transcription = process_audio_file(temp_file_path, model_name)
        
        # Clean up
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            
        return transcription.strip()
    except Exception as e:
        logging.error(f"Error in process_audio: {str(e)}")
        return ""

def process_audio_file(file_path, model_name=CURRENT_MODEL, model_size=None):
    """
    Process a complete audio file with the selected STT model
    """
    try:
        # Load and preprocess audio
        waveform, sample_rate = torchaudio.load(file_path)
        
        # Convert to mono if stereo
        if waveform.shape[0] > 1:
            waveform = torch.mean(waveform, dim=0, keepdim=True)
        
        # Resample to 16kHz if needed
        if sample_rate != 16000:
            resampler = torchaudio.transforms.Resample(orig_freq=sample_rate, new_freq=16000)
            waveform = resampler(waveform)
            sample_rate = 16000
        
        # Save preprocessed audio to temporary file
        temp_file_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.wav")
        torchaudio.save(temp_file_path, waveform, sample_rate)
        
        # Apply noise reduction preprocessing if needed
        from preprocessing_noisy_audio import save_audio
        cleaned_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}_cleaned.wav")
        cleaned_path = save_audio(temp_file_path, output_path=cleaned_path)
        
        # Load or get the model
        model = load_model(model_name, model_size)
        
        # Transcribe with the selected model
        if model_name == "faster_whisper":
            segments, info = model.transcribe(cleaned_path, beam_size=5)
            transcription = " ".join([segment.text for segment in segments])
        
        elif model_name == "whisper":
            result = model.transcribe(cleaned_path)
            transcription = result["text"]
        
        elif model_name == "wav2vec2":
            waveform, sample_rate = torchaudio.load(cleaned_path)
            if sample_rate != 16000:
                resampler = torchaudio.transforms.Resample(orig_freq=sample_rate, new_freq=16000)
                waveform = resampler(waveform)
            
            if waveform.shape[0] > 1:
                waveform = torch.mean(waveform, dim=0, keepdim=True)
                
            input_values = model["tokenizer"](waveform.squeeze().numpy(), return_tensors="pt").input_values
            with torch.no_grad():
                logits = model["model"](input_values).logits
            
            predicted_ids = torch.argmax(logits, dim=-1)
            transcription = model["tokenizer"].decode(predicted_ids[0])
        
        elif model_name == "nemo":
            transcription = model.transcribe([cleaned_path])[0]
        
        elif model_name == "seamless":
            transcription = model.transcribe_file(file_path=cleaned_path)

        elif model_name == "groqasr":
            from model_runner import transcribe
            transcription = transcribe(audio_path=cleaned_path, model="groqasr")
        
        else:
            raise ValueError(f"Unknown model: {model_name}")
        
        # Clean up temporary files
        for path in [temp_file_path, cleaned_path]:
            if os.path.exists(path):
                os.remove(path)
                
        return transcription.strip()
    except Exception as e:
        logging.error(f"Error in process_audio_file with model {model_name}: {str(e)}")
        raise

if __name__ == '__main__':
    # Initialize the default model at startup
    load_model(DEFAULT_MODEL)
    app.run(host='0.0.0.0', port=5000, debug=True)