def transcribe(audio_path, model="whisper", model_size="base"):
    """ 
    audio_path: The path to the audio file that needs to be transcribed
    model: The model that we will be using to transcribe the audio file, defaults to whisper
    size: The varient of the model that we will be using. defaults to 'whisper-base'
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
        # Check if it's a Hypothesis object
        if hasattr(result, "text"):
            return result.text
        return result # fallback if it’s already a string
    
    else:
        raise ValueError ("Unspported model selected")