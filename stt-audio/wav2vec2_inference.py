import argparse
import os
import torchaudio
from transformers import Wav2Vec2ForCTC, Wav2Vec2Tokenizer
import torch

def load_model(model_name="facebook/wav2vec2-base-960h"):
    print(f"[INFO] Loading Wav2Vec2 model: {model_name}")
    tokenizer = Wav2Vec2Tokenizer.from_pretrained(model_name)
    model = Wav2Vec2ForCTC.from_pretrained(model_name)
    return tokenizer, model

def transcribe_audio(tokenizer, model, audio_path):
    print(f"[INFO] Transcribing: {audio_path}")
    waveform, sample_rate = torchaudio.load(audio_path)
    
    if sample_rate != 16000:
        print(f"[INFO] Resampling from {sample_rate} to 16000 Hz")
        resampler = torchaudio.transforms.Resample(orig_freq=sample_rate, new_freq=16000)
        waveform = resampler(waveform)

    input_values = tokenizer(waveform.squeeze().numpy(), return_tensors="pt").input_values
    with torch.no_grad():
        logits = model(input_values).logits

    predicted_ids = torch.argmax(logits, dim=-1)
    transcription = tokenizer.decode(predicted_ids[0])

    print("\n--- Transcription ---")
    print(transcription)
    return transcription

def main():
    parser = argparse.ArgumentParser(description="Wav2Vec2 STT Inference")
    parser.add_argument("audio", help="Path to audio file (must be WAV format)")
    parser.add_argument("--model", default="facebook/wav2vec2-base-960h", help="Hugging Face model name")

    args = parser.parse_args()

    if not os.path.isfile(args.audio):
        print(f"[ERROR] File not found: {args.audio}")
        return

    tokenizer, model = load_model(args.model)
    transcribe_audio(tokenizer, model, args.audio)

if __name__ == "__main__":
    main()
