# STT Benchmarking 

This project benchmarks the various STT models (FAdam) on the benchmarks (Librispeech) dataset using Word Error Rate (WER) and Character Error Rate (CER). The results are saved in a `JSONL` format for analysis.

## Requirements

1. Set up a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate
```

Note: Make sure cmake is installed for brew.

2. Install dependencies
```bash
brew install sox
pip install -r requirements.txt
```

## Run
```bash
python stt_benchmark.py
```