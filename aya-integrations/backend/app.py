from flask import Flask, request, jsonify
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
from preprocessing_noisy_audio import noise_reduction_with_estimation, apply_vad

load_dotenv()

# Load environment variables for Cohere API
COHERE_API_KEY = os.getenv("COHERE_API_KEY")

app = Flask(__name__)
CORS(app, resources={
    r"/*": {"origins": ["http://localhost:3000"]}
})  # Enable CORS for all routes
sock = Sock(app)
logging.basicConfig(level=logging.INFO)

# Initialize faster-whisper model - load once at startup for efficiency
model = WhisperModel("base", device="cpu")  # Use "cuda" if you have a compatible GPU
logging.info("Faster-Whisper model loaded successfully")

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
                #print(json_data, audio_data)
                
                if audio_data:
                    # Decode base64 audio data
                    audio_bytes = base64.b64decode(audio_data)
                    
                    # Process with your STT model
                    transcription = process_audio(audio_bytes, session_id)
                    
                    # Only send back if there's actual transcription
                    if transcription:
                        ws.send(json.dumps({
                            'transcription': transcription,
                            'timestamp': time.time()
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
    
    # Create a temporary file
    temp_file_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.webm")
    audio_file.save(temp_file_path)
    
    try:
        # Process with your STT model
        transcription = process_audio_file(temp_file_path)
        return jsonify({'transcription': transcription})
    except Exception as e:
        logging.error(f"Error transcribing audio: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        # Clean up temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)

@app.route('/aya-response', methods=['POST'])
def get_aya_response():
    """
    Endpoint to send transcribed text to Cohere's Aya Vision API and return the response
    """
    # if not COHERE_API_KEY:
    #     return jsonify({'error': 'COHERE_API_KEY not configured'}), 500
        
    try:
        # Get request data
        data = request.json
        if not data or 'message' not in data:
            return jsonify({'error': 'No message provided'}), 400
            
        user_message = data['message']
        chat_history = data.get('chatHistory', [])
        image_data = data.get('image')  # Optional image data in base64
        
        # Configure Aya Vision API request
        headers = {
            'Authorization': f'Bearer {COHERE_API_KEY}',
            'Content-Type': 'application/json'
        }
        
        # Prepare request body
        api_request = {
            "message": user_message,
            "chat_history": format_chat_history(chat_history)
        }
        
        # Add image if provided
        if image_data:
            api_request["attachments"] = [{"source": {"type": "base64", "media_type": "image/jpeg", "data": image_data}}]
        
        # Call Cohere API
        response = requests.post(
            'https://api.cohere.ai/v1/chat',
            headers=headers,
            json=api_request
        )
        
        # Ensure the request was successful
        response.raise_for_status()
        
        # Parse the response
        result = response.json()
        
        return jsonify({
            'response': result.get('text', ''),
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

def format_chat_history(chat_history):
    """
    Format chat history for Cohere API
    """
    formatted_history = []
    for msg in chat_history:
        role = "USER" if not msg.get('isBot', False) else "CHATBOT"
        formatted_history.append({
            "role": role,
            "message": msg.get('content', '')
        })
    return formatted_history

def process_audio(audio_bytes, session_id):
    """
    Process audio bytes with the STT model
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
            
        # Apply preprocessing for noise reduction
        # cleaned_audio = noise_reduction_with_estimation(audio_np, 16000)
        # cleaned_audio = apply_vad(cleaned_audio, 16000)
        cleaned_audio = audio_np
        if cleaned_audio is None or len(cleaned_audio) == 0:
            logging.warning("No audio left after VAD")
            return ""
        
        # Save as temporary file for Faster-Whisper to process
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
        
        # Use Faster-Whisper for transcription
        segments, info = model.transcribe(temp_file_path, beam_size=5)
        
        # Combine all segments into a single transcription
        transcription = " ".join([segment.text for segment in segments])
        
        # Clean up
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
            
        return transcription.strip()
    except Exception as e:
        logging.error(f"Error in process_audio: {str(e)}")
        return ""

def process_audio_file(file_path):
    """
    Process a complete audio file with the STT model
    """
    try:
        # Load and preprocess audio
        waveform, sample_rate = torchaudio.load(file_path)
        
        # Convert to mono if stereo
        if waveform.shape[0] > 1:
            waveform = torch.mean(waveform, dim=0, keepdim=True)
        
        # Save preprocessed audio to temporary file
        temp_file_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}.wav")
        torchaudio.save(temp_file_path, waveform, sample_rate)
        
        # Apply preprocessing
        cleaned_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4()}_cleaned.wav")
        
        # Use your existing preprocessing function
        from preprocessing_noisy_audio import save_audio
        cleaned_path = save_audio(temp_file_path, output_path=cleaned_path)
        
        # Transcribe with Faster-Whisper
        segments, info = model.transcribe(cleaned_path, beam_size=5)
        transcription = " ".join([segment.text for segment in segments])
        
        # Clean up temporary files
        for path in [temp_file_path, cleaned_path]:
            if os.path.exists(path):
                os.remove(path)
                
        return transcription
    except Exception as e:
        logging.error(f"Error in process_audio_file: {str(e)}")
        raise

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)