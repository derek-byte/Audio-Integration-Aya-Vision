import argparse
import os
import torch
import torchaudio
from nemo.collections.asr.models import ASRModel

def load_model(model_name="stt_en_conformer_ctc_small"):
    print(f"Loading NeMo ASR model: {model_name}")
    model = ASRModel.from_pretrained(model_name=model_name)
    return model

def preprocess_audio(audio_path):
    waveform, sample_rate = torchaudio.load(audio_path)

    # Convert stereo to mono if needed
    if waveform.shape[0] > 1:
        print(f"Converting stereo to mono (channels: {waveform.shape[0]})")
        waveform = torch.mean(waveform, dim=0, keepdim=True)
        mono_path = "temp_mono.wav"
        torchaudio.save(mono_path, waveform, sample_rate)
        return mono_path

    return audio_path

def transcribe_audio(model, audio_path):
    processed_path = preprocess_audio(audio_path)
    print(f"Transcribing: {processed_path}")
    transcription = model.transcribe([processed_path])[0]

    print("\n--- Transcription ---")
    print(transcription)
    return transcription

def main():
    parser = argparse.ArgumentParser(description="NVIDIA NeMo STT Inference")
    parser.add_argument("audio", help="Path to audio file (.wav)")
    parser.add_argument("--model", default="stt_en_conformer_ctc_small", help="Model name from NeMo (e.g., stt_en_conformer_ctc_small)")

    args = parser.parse_args()

    if not os.path.isfile(args.audio):
        print(f"File not found: {args.audio}")
        return

    model = load_model(args.model)
    transcribe_audio(model, args.audio)

if __name__ == "__main__":
    main()
