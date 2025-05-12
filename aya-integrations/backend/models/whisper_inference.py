import whisper
import argparse
import os

def load_model(model_size="base"):
    print(f"Loading Whisper model: {model_size}")
    return whisper.load_model(model_size)

def transcribe_audio(model, audio_path):
    print(f"Transcribing: {audio_path}")
    result = model.transcribe(audio_path)
    
    print("\n--- Transcription ---")
    print(result["text"])
    print(f"\nDetected Language: {result['language']}")
    return result

def main():
    parser = argparse.ArgumentParser(description="Local Whisper STT Inference")
    parser.add_argument("audio", help="Path to audio file (.wav, .mp3, .m4a, etc.)")
    parser.add_argument("--model", default="base", help="Model size: tiny, base, small, medium, large")

    args = parser.parse_args()

    if not os.path.isfile(args.audio):
        print(f"File not found: {args.audio}")
        return

    model = load_model(args.model)
    transcribe_audio(model, args.audio)

if __name__ == "__main__":
    main()
