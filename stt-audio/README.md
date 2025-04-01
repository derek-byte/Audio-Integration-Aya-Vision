# Whisper STT Pipeline

This is a Python-based speech-to-text (STT) pipeline using [OpenAI's Whisper](https://github.com/openai/whisper).  
It transcribes local audio files into text using the Whisper model.
- Detects spoken language automatically
- The Whisper model sizes: `tiny`, `base`, `small`, `medium`, `large`

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/derek-byte/Audio-Integration-Aya-Vision.git
```

### 2. Create a virtual environment (Python 3.10+)

```bash
python -m venv stt_venv
source stt_venv/bin/activate
```

### 3. Install dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

Also install `ffmpeg` system-wide:

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt install ffmpeg
```

---

## Usage

Run the transcription script:

```bash
python whisper_inference.py path/to/audio.wav --model base
```

Arguments:
- `--model` (optional): Choose from `tiny`, `base`, `small`, `medium`, `large`
- Default is `base`

---

## Output

You'll see output like:

```
[INFO] Transcribing: harvard.wav

--- Transcription ---
She had your dark suit in greasy wash water all year.

[INFO] Detected Language: en
```

---

## 📂 Project Structure

```
whisper-stt-pipeline/
├── whisper_inference.py         # Main script
├── requirements.txt             # Python dependencies
└── README.md                   
```

---

## Whisper Models (Quick Reference)

| Model   | Size     | Speed     | Accuracy  |
|---------|----------|-----------|-----------|
| `tiny`  | ~39 MB   | Fastest   | Lowest    |
| `base`  | ~74 MB   | Fast      | Good      |
| `small` | ~244 MB  | Medium    | Better    |
| `medium`| ~769 MB  | Slower    | High      |
| `large` | ~1550 MB | Slowest   | Highest   |
