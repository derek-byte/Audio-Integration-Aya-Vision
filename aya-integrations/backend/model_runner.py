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
    
    elif model == "seamless":
        from stt_audio.seamless_inference import load_model, get_seamless_default_config
        model_config = get_seamless_default_config()
        # uncomment the following line to modify the model_config in order to run seamless on cpu
        # model_config["device"] = "cpu"
        wrapper = load_model(model_config=model_config)
        result = wrapper.transcribe_file(file_path=audio_path)
        return result
    
    else:
        raise ValueError ("Unspported model selected")