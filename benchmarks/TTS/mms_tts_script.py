import os
import torch
import pandas as pd
import torchaudio
import numpy as np
from transformers import VitsTokenizer, VitsModel, set_seed

# Load pre-trained VITS model and tokenizer
tokenizer = VitsTokenizer.from_pretrained("facebook/mms-tts-eng")
model = VitsModel.from_pretrained("facebook/mms-tts-eng")

# Function to load audio files
def load_audio(file_path):
    waveform, sample_rate = torchaudio.load(file_path)
    return waveform, sample_rate

# Compute MCD between reference and generated speech
def compute_mcd(reference_audio, generated_audio, sample_rate=16000):
    # Convert audio to mel spectrogram
    mel_transform = torchaudio.transforms.MelSpectrogram(sample_rate=sample_rate)

    reference_mel = mel_transform(reference_audio)
    generated_mel = mel_transform(generated_audio)

    # Normalize
    reference_mel = reference_mel / reference_mel.max()
    generated_mel = generated_mel / generated_mel.max()

    # Flatten and convert to numpy
    reference_mel = reference_mel.numpy().flatten()
    generated_mel = generated_mel.numpy().flatten()

    # Match lengths (truncate to shortest length)
    min_len = min(len(reference_mel), len(generated_mel))
    reference_mel = reference_mel[:min_len]
    generated_mel = generated_mel[:min_len]

    # Compute simple MCD (Euclidean between mel features)
    mcd = np.sqrt(np.mean((reference_mel - generated_mel) ** 2))
    return mcd

# Benchmarking function
def benchmark_tts_model(csv_path, audio_folder):
    data = pd.read_csv(csv_path)
    mcd_scores = []
    results = []

    for _, row in data.iterrows():
        text = row['transcript']
        audio_filename = row['audio_name']
        audio_path = os.path.join(audio_folder, audio_filename)

        if not os.path.exists(audio_path):
            print(f"Audio file {audio_filename} not found. Skipping.")
            continue

        # Tokenize input
        inputs = tokenizer(text, return_tensors="pt")

        with torch.no_grad():
            outputs = model(**inputs)
            generated_waveform = outputs.waveform[0].unsqueeze(0)  # Shape: [1, samples]

        reference_audio, _ = load_audio(audio_path)

        # Resample if needed
        if reference_audio.shape[0] > 1:
            reference_audio = reference_audio.mean(dim=0, keepdim=True)

        mcd_score = compute_mcd(reference_audio, generated_waveform)
        mcd_scores.append(mcd_score)

        results.append({
            "text": text,
            "mcd_score": mcd_score,
            "audio_path": audio_path
        })

        print(f"Text: {text}")
        print(f"MCD Score: {mcd_score:.4f}\n")

    return results, np.mean(mcd_scores)

# File paths
csv_path = r'C:\Users\babat\Downloads\TTS_SCRIPT\filtered_fleurs_train.csv' 
audio_folder = r'C:\Users\babat\Downloads\Fleurs train english'  

# Run benchmark
results, avg_mcd = benchmark_tts_model(csv_path, audio_folder)
print(f"Average MCD: {avg_mcd:.4f}")
