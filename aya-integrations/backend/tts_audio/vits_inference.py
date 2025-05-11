# tts_audio/vits_inference.py

import os
import uuid
import torch
import torchaudio
from transformers import VitsTokenizer, VitsModel

DEFAULT_MODEL_NAME = "facebook/mms-tts-eng"

def load_model_and_tokenizer(model_name=DEFAULT_MODEL_NAME):
    """
    Loads the VITS tokenizer and model from HuggingFace.

    Parameters:
    - model_name: Model identifier or path.

    Returns:
    - tokenizer, model
    """
    tokenizer = VitsTokenizer.from_pretrained(model_name)
    model = VitsModel.from_pretrained(model_name)
    model.eval()
    return tokenizer, model

def save_waveform(waveform, sample_rate=16000, output_dir="generated_audios"):
    """
    Saves a PyTorch waveform tensor to disk as a .wav file.

    Returns:
    - Full path to the saved audio file.
    """
    os.makedirs(output_dir, exist_ok=True)
    audio_id = f"{uuid.uuid4()}.wav"
    audio_path = os.path.abspath(os.path.join(output_dir, audio_id))
    torchaudio.save(audio_path, waveform, sample_rate)
    return audio_path

def synthesize_audio(text, model_name=DEFAULT_MODEL_NAME, output_path=None):
    """
    Synthesizes speech from text using a VITS model.

    Parameters:
    - text: The input text to synthesize.
    - model_name: Model name or path.
    - output_path: Optional full output path for the audio file.

    Returns:
    - Path to generated audio file.
    """
    tokenizer, model = load_model_and_tokenizer(model_name)
    inputs = tokenizer(text, return_tensors="pt")

    with torch.no_grad():
        outputs = model(**inputs)
        waveform = outputs.waveform[0].unsqueeze(0)

    if output_path is None:
        return save_waveform(waveform)
    else:
        torchaudio.save(output_path, waveform, sample_rate=16000)
        return output_path
