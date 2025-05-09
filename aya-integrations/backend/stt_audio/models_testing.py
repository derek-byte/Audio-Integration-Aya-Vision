import os
import time
import torch
import torchaudio
from jiwer import wer, cer, mer, compute_measures

# ---------------- Metrics ----------------
def compute_metrics(ref, hyp, duration, runtime):
    return {
        "WER": wer(ref, hyp),
        "CER": cer(ref, hyp),
        "MER": mer(ref, hyp),
        "RTF": runtime / duration if duration > 0 else 0.0
    }

def print_metrics(metrics):
    for k, v in metrics.items():
        print(f"{k}: {v:.4f}")

# ---------------- Whisper ----------------
def transcribe_whisper(audio_path, reference_text, duration):
    import whisper
    whisper_models = ["tiny", "base", "small", "medium", "large"]
    print("\n=== Whisper Inference ===")

    for model_size in whisper_models:
        print(f"\n[Whisper: {model_size}]")
        model = whisper.load_model(model_size)

        start = time.time()
        result = model.transcribe(audio_path)
        end = time.time()

        hyp = result["text"].strip()
        print(hyp)
        print(f"[Detected Language: {result['language']}]")
        metrics = compute_metrics(reference_text, hyp, duration, end - start)
        print_metrics(metrics)

# ---------------- Wav2Vec2 ----------------
def transcribe_wav2vec2(audio_path, reference_text, duration):
    from transformers import Wav2Vec2ForCTC, Wav2Vec2Tokenizer

    models = [
        "facebook/wav2vec2-base-960h",
        "facebook/wav2vec2-large-960h",
        "facebook/wav2vec2-large-960h-lv60-self",
        "facebook/wav2vec2-large-xlsr-53"
    ]

    waveform, sample_rate = torchaudio.load(audio_path)
    if sample_rate != 16000:
        resampler = torchaudio.transforms.Resample(orig_freq=sample_rate, new_freq=16000)
        waveform = resampler(waveform)

    if waveform.shape[0] > 1:
        waveform = torch.mean(waveform, dim=0, keepdim=True)

    print("\n=== Wav2Vec2 Inference ===")
    for model_name in models:
        print(f"\n[Wav2Vec2: {model_name}]")
        tokenizer = Wav2Vec2Tokenizer.from_pretrained(model_name)
        model = Wav2Vec2ForCTC.from_pretrained(model_name)

        start = time.time()
        input_values = tokenizer(waveform.squeeze().numpy(), return_tensors="pt").input_values
        with torch.no_grad():
            logits = model(input_values).logits
        predicted_ids = torch.argmax(logits, dim=-1)
        hyp = tokenizer.decode(predicted_ids[0])
        end = time.time()

        print(hyp)
        metrics = compute_metrics(reference_text, hyp, duration, end - start)
        print_metrics(metrics)

# ---------------- NeMo ----------------
def transcribe_nemo(audio_path, reference_text, duration):
    from nemo.collections.asr.models import ASRModel

    models = [
        "stt_en_conformer_ctc_small",
        "stt_en_conformer_ctc_medium",
        "stt_en_conformer_ctc_large"
    ]

    waveform, sample_rate = torchaudio.load(audio_path)
    if waveform.shape[0] > 1:
        waveform = torch.mean(waveform, dim=0, keepdim=True)
        torchaudio.save("temp_mono.wav", waveform, sample_rate)
        audio_path = "temp_mono.wav"

    print("\n=== NeMo Inference ===")
    for model_name in models:
        print(f"\n[NeMo: {model_name}]")
        model = ASRModel.from_pretrained(model_name=model_name)

        start = time.time()
        hyp = model.transcribe([audio_path])[0]
        end = time.time()

        print(hyp)
        metrics = compute_metrics(reference_text, hyp, duration, end - start)
        print_metrics(metrics)


# ---------------- Seamless ----------------
def transcribe_seamless(audio_path, reference_text, duration):
    from seamless_inference import get_seamless_default_config, load_model
    wrapper = load_model(model_config=get_seamless_default_config())
    print(f"\n[Seamless Streaming]")
    start = time.time()
    hyp = wrapper.transcribe_file(
        file_path=audio_path
    )
    end = time.time()

    print(hyp)
    # metrics = compute_metrics(reference_text, hyp, duration, end - start)
    print_metrics(metrics)

# ---------------- Main ----------------
def main():
    import argparse
    parser = argparse.ArgumentParser(description="Benchmark STT models with metrics")
    parser.add_argument("audio", help="Path to .wav audio file")
    parser.add_argument("reference", help="Ground truth transcript (text file)")
    parser.add_argument("--models", help="models to run in the benchmark on", nargs='+', default=["whisper", "wav2vec2", "nemo", "seamless"], type=str)
    args = parser.parse_args()

    if not os.path.isfile(args.audio):
        print(f" Audio file not found: {args.audio}")
        return
    if not os.path.isfile(args.reference):
        print(f" Reference file not found: {args.reference}")
        return

    with open(args.reference, "r", encoding="utf-8") as f:
        reference_text = f.read().strip()

    info = torchaudio.info(args.audio)
    duration = info.num_frames / info.sample_rate

    if "whisper" in args.models:
        transcribe_whisper(args.audio, reference_text, duration)
    
    if "wav2vec2" in args.models:
        transcribe_wav2vec2(args.audio, reference_text, duration)
    
    if "nemo" in args.models:
        transcribe_nemo(args.audio, reference_text, duration)
    
    if "seamless" in args.models:
        transcribe_seamless(args.audio, reference_text, duration)

if __name__ == "__main__":
    main()
