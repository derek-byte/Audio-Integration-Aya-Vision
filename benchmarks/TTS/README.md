##  TTS Benchmarking

This folder contains scripts and resources for benchmarking the Meta MMS Text-to-Speech (TTS) model.

The evaluation is based on Mel Cepstral Distortion (MCD), a metric that measures the similarity between generated and reference speech.

##  Requirements

1. **Set up your virtual environment (Windows)**
   ```bash
   python -m venv venv
   .\venv\Scripts\activate
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the script**
   ```bash
   python mms_tts_script.py
   ```
