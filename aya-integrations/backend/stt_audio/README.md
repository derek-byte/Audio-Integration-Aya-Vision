# STT Inference Pipeline (Whisper, Wav2Vec2, NeMo)

This is a Python-based speech-to-text (STT) inference pipeline supporting multiple backends:
- [OpenAI Whisper](https://github.com/openai/whisper)
- [Wav2Vec2 (Hugging Face)](https://huggingface.co/facebook/wav2vec2-base-960h)
- [NVIDIA NeMo](https://github.com/NVIDIA/NeMo)


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

Also install `ffmpeg`

---

## Usage

Run the transcription script:

```bash
python main.py path/to/audio.wav --backend whisper --model base
```

Arguments:
- audio (required): Path to the audio file
- `--model`: Choose from whisper, wav2vec2, or nemo (default: whisper)
- `--size`: Model size name depending on the backend

---

## Examples

Whisper

```bash
python whisper_inference.py sample.wav --model whisper --size base
```
Wav2Vec2

```bash
python whisper_inference.py sample.wav --model wav2vec2 --size facebook/wav2vec2-base-960h
```
Nemo

```bash
python whisper_inference.py sample.wav --model nemo --size stt_en_conformer_ctc_small
```

## Supported Sizes For Each Model

| Whisper Models              | Wav2Vec2 Models                         | NeMo Models                        |
| `tiny`                      | `facebook/wav2vec2-base-960h`           | `stt_en_conformer_ctc_small`       |
| `base`                      | `facebook/wav2vec2-large-960h`          | `stt_en_conformer_ctc_medium`      |
| `small`                     | `facebook/wav2vec2-large-960h-lv60-self`| `stt_en_conformer_ctc_large`       |
| `medium`                    | `facebook/wav2vec2-large-xlsr-53`       |                                    |
| `large`                     |                                         |                                    |

