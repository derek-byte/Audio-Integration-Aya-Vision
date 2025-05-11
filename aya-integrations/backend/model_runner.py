from pathlib import Path
import os


def transcribe(audio_path, model="whisper", model_size="base"):
    """ 
    Transcribe audio using various models.
    
    Parameters:
    - audio_path: Path to the audio file.
    - model: Model type to use (e.g., whisper, wav2vec2, nemo, seamless, groq).
    - model_size: Size/variant of the model (e.g., base, large).
    """
    if model == "whisper":
        from stt_audio.whisper_inference import load_model, transcribe_audio
        model = load_model(model_size)
        return transcribe_audio(model=model, audio_path=audio_path)["text"]
    
    elif model == "wav2vec2":
        from stt_audio.wav2vec2_inference import load_model, transcribe_audio
        tokenizer, model = load_model(model_size)
        return transcribe_audio(tokenizer, model, audio_path)
    
    elif model == "nemo":
        from stt_audio.nemo_inference import load_model, transcribe_audio
        model = load_model(model_size)
        result = transcribe_audio(model, audio_path)
        return result.text if hasattr(result, "text") else result

    elif model == "seamless":
        from stt_audio.seamless_inference import load_model, get_seamless_default_config
        model_config = get_seamless_default_config()
        # model_config["device"] = "cpu"  # Optional: force CPU usage
        wrapper = load_model(model_config=model_config)
        return wrapper.transcribe_file(file_path=audio_path)

    elif model == "groqasr":
        from groq import Groq
        import os

        # Load API key from environment variable for security
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError("GROQ_API_KEY not set in environment variables.")

        client = Groq(api_key=api_key)

        with open(audio_path, "rb") as file:
            translation = client.audio.translations.create(
                file=(audio_path, file.read()),
                model="whisper-large-v3",
                prompt="Specify context or spelling",  # Optional
                response_format="json",
                temperature=0.0
            )
            return translation.text

    else:
        raise ValueError("Unsupported model selected")


def synthesize_speech(text, model="groqtts", voice="Aaliyah-PlayAI", output_filename="speech.wav"):
    """
    Synthesizes speech from text using the specified model.

    Parameters:
    - text: Text to convert to speech.
    - model: Speech synthesis model/provider (e.g., 'groq').
    - voice: Voice to use (if supported by the model).
    - output_filename: Path to save the generated speech audio.

    Returns:
    - Path to the synthesized audio file.
    """
    if model == "groqtts":
        from groq import Groq

        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise EnvironmentError("GROQ_API_KEY not set in environment variables.")
        
        client = Groq(api_key=api_key)
        output_path = Path(output_filename)

        response = client.audio.speech.create(
            model="playai-tts",
            voice=voice,
            response_format="wav",
            input=text,
        )
        response.write_to_file(output_path)
        return str(output_path)
    
    elif model == "speecht5":
        from tts_audio.speech_t5_inference import load_model, synthesize_audio
        t5_pipeline = load_model()
        print("############### about to write the audio")
        return synthesize_audio(t5_pipeline, text, output_filename)

    elif model == "vits":
        from tts_audio.vits_inference import synthesize_audio
        return synthesize_audio(text, output_path=output_filename)

    else:
        raise ValueError("Unsupported speech synthesis model selected.")
