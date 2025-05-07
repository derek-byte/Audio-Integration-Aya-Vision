# Examples of integrating different STT models with your Flask backend

# ============================================================
# 1. OpenAI Whisper Integration
# ============================================================
def integrate_whisper():
    import whisper
    import tempfile
    
    # Load the model only once at startup
    model = whisper.load_model("base")  # Options: tiny, base, small, medium, large
    
    def process_audio_chunk(audio_bytes):
        """Process a chunk of audio with Whisper"""
        with tempfile.NamedTemporaryFile(suffix='.webm', delete=True) as temp_file:
            temp_file.write(audio_bytes)
            temp_file.flush()
            
            # Process with Whisper
            result = model.transcribe(temp_file.name, fp16=False)
            return result["text"]
    
    return process_audio_chunk

# ============================================================
# 2. Mozilla DeepSpeech Integration
# ============================================================
def integrate_deepspeech():
    import deepspeech
    import numpy as np
    import wave
    import tempfile
    
    # Load DeepSpeech model
    model_file_path = 'path/to/deepspeech-0.9.3-models.pbmm'
    model = deepspeech.Model(model_file_path)
    
    # Optional: Add scorer for better accuracy
    scorer_file_path = 'path/to/deepspeech-0.9.3-models.scorer'
    model.enableExternalScorer(scorer_file_path)
    
    def process_audio_chunk(audio_bytes):
        """Process a chunk of audio with DeepSpeech"""
        # Save bytes to a temporary WAV file (DeepSpeech works better with WAV)
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=True) as temp_wav:
            # Convert webm to wav if needed
            # This is simplified - you might need additional conversion logic
            with wave.open(temp_wav.name, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(16000)
                wf.writeframes(audio_bytes)
            
            # Process with DeepSpeech
            with wave.open(temp_wav.name, 'rb') as wf:
                buffer = np.frombuffer(wf.readframes(wf.getnframes()), np.int16)
                text = model.stt(buffer)
                return text
    
    return process_audio_chunk

# ============================================================
# 3. Hugging Face Transformers (wav2vec2) Integration
# ============================================================
def integrate_huggingface():
    from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
    import torch
    import soundfile as sf
    import tempfile
    import io
    
    # Load model and processor
    processor = Wav2Vec2Processor.from_pretrained("facebook/wav2vec2-base-960h")
    model = Wav2Vec2ForCTC.from_pretrained("facebook/wav2vec2-base-960h")
    
    def process_audio_chunk(audio_bytes):
        """Process a chunk of audio with wav2vec2"""
        # Convert bytes to audio array
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=True) as temp_file:
            temp_file.write(audio_bytes)
            temp_file.flush()
            
            # Load audio
            speech_array, sampling_rate = sf.read(temp_file.name)
            
            # Resample if needed (wav2vec2 expects 16kHz)
            if sampling_rate != 16000:
                # You would need to implement resampling here
                # For simplicity, we'll assume 16kHz input
                pass
            
            # Tokenize
            input_values = processor(speech_array, sampling_rate=16000, return_tensors="pt").input_values
            
            # Retrieve logits
            with torch.no_grad():
                logits = model(input_values).logits
            
            # Take argmax and decode
            predicted_ids = torch.argmax(logits, dim=-1)
            transcription = processor.batch_decode(predicted_ids)
            
            return transcription[0]
    
    return process_audio_chunk

# ============================================================
# 4. Integration with Cloud-based STT Services
# ============================================================

# Google Cloud Speech-to-Text
def integrate_google_cloud_stt():
    from google.cloud import speech
    import io
    
    # Initialize client
    client = speech.SpeechClient()
    
    def process_audio_chunk(audio_bytes):
        """Process a chunk of audio with Google Cloud STT"""
        audio = speech.RecognitionAudio(content=audio_bytes)
        
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.WEBM_OPUS,
            sample_rate_hertz=16000,
            language_code="en-US",
        )
        
        response = client.recognize(config=config, audio=audio)
        
        transcript = ""
        for result in response.results:
            transcript += result.alternatives[0].transcript
            
        return transcript
    
    return process_audio_chunk

# AWS Transcribe
def integrate_aws_transcribe():
    import boto3
    import uuid
    import time
    import tempfile
    
    # Initialize client
    transcribe = boto3.client('transcribe')
    s3 = boto3.client('s3')
    bucket_name = 'your-transcription-bucket'
    
    def process_audio_chunk(audio_bytes):
        """Process a chunk of audio with AWS Transcribe"""
        # AWS Transcribe doesn't support direct audio bytes
        # We need to upload to S3 first
        job_name = f"transcription-{uuid.uuid4()}"
        object_key = f"audio/{job_name}.webm"
        
        # Upload audio to S3
        s3.put_object(
            Bucket=bucket_name,
            Key=object_key,
            Body=audio_bytes
        )
        
        # Start transcription job
        transcribe.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={
                'MediaFileUri': f"s3://{bucket_name}/{object_key}"
            },
            MediaFormat='webm',
            LanguageCode='en-US'
        )
        
        # Wait for completion
        while True:
            status = transcribe.get_transcription_job(TranscriptionJobName=job_name)
            if status['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
                break
            time.sleep(0.5)
        
        if status['TranscriptionJob']['TranscriptionJobStatus'] == 'COMPLETED':
            import requests
            
            # Get the transcript URL and download it
            transcript_uri = status['TranscriptionJob']['Transcript']['TranscriptFileUri']
            response = requests.get(transcript_uri)
            transcript_data = response.json()
            
            # Extract transcript text
            transcript = transcript_data['results']['transcripts'][0]['transcript']
            
            # Clean up S3
            s3.delete_object(Bucket=bucket_name, Key=object_key)
            
            return transcript
        else:
            return "Transcription failed"
    
    return process_audio_chunk

# ============================================================
# Usage in your Flask app
# ============================================================

def integrate_with_flask_app():
    # Choose which STT model to use
    STT_MODEL = "whisper"  # Options: whisper, deepspeech, huggingface, google, aws
    
    if STT_MODEL == "whisper":
        process_audio = integrate_whisper()
    elif STT_MODEL == "deepspeech":
        process_audio = integrate_deepspeech()
    elif STT_MODEL == "huggingface":
        process_audio = integrate_huggingface()
    elif STT_MODEL == "google":
        process_audio = integrate_google_cloud_stt()
    elif STT_MODEL == "aws":
        process_audio = integrate_aws_transcribe()
    else:
        raise ValueError(f"Unknown STT model: {STT_MODEL}")
    
    # Now you can use process_audio in your Flask app
    # Example:
    """
    @sock.route('/stream-audio')
    def stream_audio(ws):
        while True:
            data = ws.receive()
            json_data = json.loads(data)
            audio_data = json_data.get('audio_data')
            
            if audio_data:
                audio_bytes = base64.b64decode(audio_data)
                transcription = process_audio(audio_bytes)
                ws.send(json.dumps({
                    'transcription': transcription
                }))
    """