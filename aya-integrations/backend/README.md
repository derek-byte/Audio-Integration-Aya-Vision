# 🧠 STT/TTS Model Selector SDK with Aya Vision Integration

This Flask-based backend SDK enables dynamic speech-to-text (STT) and text-to-speech (TTS) model selection, with support for real-time transcription via WebSocket and audio file upload. Integrated with the Aya Vision API, this SDK supports multiple transcription models including Faster Whisper, Whisper, Wav2Vec2, NeMo, and SeamlessM4T, as well as TTS models like gTTS and GroqTTS.

---

## 🚀 Features

- ✅ Dynamic STT model switching via REST API
- ✅ Real-time streaming transcription using WebSockets
- ✅ Audio file upload support for batch transcription
- ✅ TTS model selection and synthesis (gTTS, GroqTTS, etc.)
- ✅ Integrated with Aya Vision for multimodal use cases
- ✅ CORS-enabled for cross-origin frontend access

---

## 🧰 Prerequisites

Make sure the following are installed on your system:

```bash
# Create and activate Python environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# System dependencies
brew install ffmpeg
brew install libsndfile
```

## 📦 Installation

1. Clone the repository:
```bash
git clone https://github.com/your-username/your-repo.git
cd your-repo
```

2. Follow the prerequisites above to set up your environment.

3. Run the Flask server:
```bash
python app.py
```

## 🌐 API Endpoints
`/set-model` `/available-models` `/transcribe` `/stream-audio` `/synthesize/audio/<filename>` `/aya-response` `/aya-response-tts`

## 🤖 Supported Models
### STT
`faster_whisper` `whisper` `wav2vec2` `nemo` `seamless`
### TTS
`gtts` `groqtts` `groqasr`