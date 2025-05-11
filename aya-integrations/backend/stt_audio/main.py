import argparse
import os
import sys
import torch
import torchaudio

from preprocessing_noisy_audio import save_audio


def transcribe_whisper(audio_path, model_size="base"):
    import whisper
    print(f"Loading Whisper model: {model_size}")
    model = whisper.load_model(model_size)

    print(f"Transcribing with Whisper: {audio_path}")
    result = model.transcribe(audio_path)

    print("\n Transcribed Text: ")
    print(result["text"])
    print(f"\n Detected Language: {result['language']}")
    return result["text"]

def transcribe_wav2vec2(audio_path, model_name="facebook/wav2vec2-base-960h"):
    from transformers import Wav2Vec2ForCTC, Wav2Vec2Tokenizer
    print(f"Loading Wav2Vec2 model: {model_name}")
    tokenizer = Wav2Vec2Tokenizer.from_pretrained(model_name)
    model = Wav2Vec2ForCTC.from_pretrained(model_name)

    waveform, sample_rate = torchaudio.load(audio_path)
    if sample_rate != 16000:
        print(f"Resampling from {sample_rate} to 16000 Hz")
        resampler = torchaudio.transforms.Resample(orig_freq=sample_rate, new_freq=16000)
        waveform = resampler(waveform)

    if waveform.shape[0] > 1:
        waveform = torch.mean(waveform, dim=0, keepdim=True)

    input_values = tokenizer(waveform.squeeze().numpy(), return_tensors="pt").input_values
    with torch.no_grad():
        logits = model(input_values).logits

    predicted_ids = torch.argmax(logits, dim=-1)
    transcription = tokenizer.decode(predicted_ids[0])

    print("\n Transcribed Text: ")
    print(transcription)
    return transcription

def preprocess_audio_for_nemo(audio_path):
    waveform, sample_rate = torchaudio.load(audio_path)
    if waveform.shape[0] > 1:
        print(f"Converting stereo to mono (channels: {waveform.shape[0]})")
        waveform = torch.mean(waveform, dim=0, keepdim=True)
        mono_path = "temp_mono.wav"
        torchaudio.save(mono_path, waveform, sample_rate)
        return mono_path
    return audio_path

def transcribe_nemo(audio_path, model_name="stt_en_conformer_ctc_small"):
    from nemo.collections.asr.models import ASRModel
    print(f"Loading NeMo model: {model_name}")
    model = ASRModel.from_pretrained(model_name=model_name)

    cleaned_path = preprocess_audio_for_nemo(audio_path)
    print(f"Transcribing with NeMo: {cleaned_path}")
    transcription = model.transcribe([cleaned_path])[0]

    print("\n Transcribed Text: ")
    print(transcription)
    return transcription

def transcribe_seamless(audio_path):
    from seamless_inference import load_model, get_seamless_default_config
    model_config = get_seamless_default_config()
    # uncomment the following line to modify the model_config in order to run seamless on cpu
    # model_config["device"] = "cpu"
    wrapper = load_model(model_config=model_config)
    print(f"\n[Seamless Streaming]")
    transcription = wrapper.transcribe_file(
        file_path=audio_path
    )

    print("\n Transcribed Text: ")
    print(transcription)
    return transcription

def main():
    parser = argparse.ArgumentParser(description="Unified STT Inference")
    parser.add_argument("audio", help="Path to audio file")
    parser.add_argument("--model", choices=["whisper", "wav2vec2", "nemo", "seamless"], default="whisper", help="STT backend to use")
    parser.add_argument("--size", default=None, help="Model name/size for the selected backend")

    args = parser.parse_args()

    if not os.path.isfile(args.audio):
        print(f"File not found: {args.audio}")
        sys.exit(1)
    
    cleaned_audio = save_audio(args.audio)

    if args.model == "whisper":
        model_size = args.size or "base"
        transcribe_whisper(cleaned_audio, model_size)

    elif args.model == "wav2vec2":
        model_name = args.size or "facebook/wav2vec2-base-960h"
        transcribe_wav2vec2(cleaned_audio, model_name)

    elif args.model == "nemo":
        model_name = args.size or "stt_en_conformer_ctc_small"
        transcribe_nemo(cleaned_audio, model_name)
    
    elif args.model == "seamless":
        transcribe_seamless(cleaned_audio)

if __name__ == "__main__":
    main()