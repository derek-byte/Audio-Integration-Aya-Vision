import librosa
import numpy as np
import soundfile as sf
import webrtcvad
import torch

def load_audio(path, sr=16000):
    audio, _ = librosa.load(path, sr=sr)
    return audio, sr

def estimate_noise_profile(audio, sr, frame_size=2048, hop_length=512):
    energy = np.array([
        np.sum(np.square(audio[i:i+frame_size]))
        for i in range(0, len(audio) - frame_size, hop_length)
    ])
    threshold = np.percentile(energy, 25)
    low_energy_indices = np.where(energy < threshold)[0]

    stft = librosa.stft(audio, n_fft=frame_size, hop_length=hop_length)
    low_energy_mag = np.abs(stft[:, low_energy_indices])
    noise_profile = np.mean(low_energy_mag, axis=1)
    return noise_profile

def noise_reduction_with_estimation(audio, sr, frame_size=2048, hop_length=512):
    noise_profile = estimate_noise_profile(audio, sr, frame_size, hop_length)

    stft_audio = librosa.stft(audio, n_fft=frame_size, hop_length=hop_length)
    magnitude, phase = np.abs(stft_audio), np.angle(stft_audio)

    cleaned_magnitude = np.maximum(magnitude - noise_profile[:, np.newaxis], 0)
    cleaned_audio = librosa.istft(cleaned_magnitude * np.exp(1j * phase), hop_length=hop_length)
    return cleaned_audio

def apply_vad(audio, sr, frame_duration_ms=30):
    if sr not in (8000, 16000, 32000, 48000):
        raise ValueError(f"Unsupported sample rate {sr} for VAD")

    vad = webrtcvad.Vad(2)
    samples = (audio * 32768).astype(np.int16) 
    bytes_audio = samples.tobytes()

    frame_length = int(sr * frame_duration_ms / 1000) 
    byte_length = frame_length * 2 

    speech_bytes = bytearray()
    for i in range(0, len(bytes_audio) - byte_length + 1, byte_length):
        frame = bytes_audio[i : i + byte_length]
        if len(frame) == byte_length and vad.is_speech(frame, sr):
            speech_bytes.extend(frame)

    if len(speech_bytes) == 0:
        return audio

    speech_int16 = np.frombuffer(speech_bytes, dtype=np.int16)
    return speech_int16.astype(np.float32) / 32768.0

def extract_mfcc(audio, sr, n_mfcc=13, hop_length=160):
    mfccs = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=n_mfcc, hop_length=hop_length)
    return mfccs

def frame_audio(audio, frame_size, hop_size):
    num_frames = 1 + int((len(audio) - frame_size) / hop_size)
    frames = np.stack([
        audio[i * hop_size : i * hop_size + frame_size] for i in range(num_frames)
    ])
    return frames

def save_audio(audio_path, output_path="temp_cleaned_audio.wav", apply_vad_filter=True):
    audio, sr = load_audio(audio_path, sr=16000)

    cleaned_audio = noise_reduction_with_estimation(audio, sr)

    if apply_vad_filter:
        cleaned_audio = apply_vad(cleaned_audio, sr)

    sf.write(output_path, cleaned_audio, sr)
    return output_path
