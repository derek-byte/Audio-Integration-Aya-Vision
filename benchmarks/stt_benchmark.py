import torchaudio
import torchaudio.datasets as datasets
from jiwer import wer, cer
import torch
import json
from tqdm import tqdm
import re

torchaudio.set_audio_backend("sox_io")

# Load pretrained Wav2Vec2 model
bundle = torchaudio.pipelines.WAV2VEC2_ASR_BASE_960H
model = bundle.get_model()
model.eval()
labels = bundle.get_labels()

# Greedy decoder function
def greedy_decode(emission):
    indices = torch.argmax(emission, dim=-1)
    tokens = [labels[i] for i in indices]
    return "".join([t if t != "|" else " " for t in tokens])  # "|" represents space

# Normalize text
def normalize_text(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z' ]", "", text)  # Remove punctuation but keep apostrophes
    return text

# Speech-to-text function
def wav2vec2_stt_model(audio_waveform, sample_rate):
    """Convert waveform to text using the Wav2Vec2 model."""
    if sample_rate != 16000:
        audio_waveform = torchaudio.transforms.Resample(sample_rate, 16000)(audio_waveform)

    # Ensure the waveform is 2D: (batch, time)
    if audio_waveform.dim() == 1:
        audio_waveform = audio_waveform.unsqueeze(0)  # Add batch dimension if missing
    elif audio_waveform.dim() == 3:
        audio_waveform = audio_waveform.squeeze(0)  # Remove extra batch dim if present
    
    with torch.no_grad():
        emission, _ = model(audio_waveform)  # Now it should be (batch, time)
    
    predicted_text = greedy_decode(emission[0])
    return predicted_text


# Load test dataset
test_set = datasets.LIBRISPEECH("./data", url="test-clean", download=True)
result_file = "results/Wav2Vec2_stt_benchmark_results.jsonl" # Adjust as needed

num_samples = 100  # Adjust as needed
wer_scores, cer_scores = [], []
results = []

for i in tqdm(range(num_samples), desc="Processing samples", unit="sample"):
    waveform, sample_rate, transcript, _, _, _ = test_set[i]
    
    predicted_text = wav2vec2_stt_model(waveform, sample_rate)
    
    transcript = normalize_text(transcript)
    predicted_text = normalize_text(predicted_text)

    wer_score = wer(transcript, predicted_text)
    cer_score = cer(transcript, predicted_text)
    
    wer_scores.append(wer_score)
    cer_scores.append(cer_score)
    
    result = {
        "sample": i+1,
        "ground_truth": transcript,
        "predicted": predicted_text,
        "wer": wer_score,
        "cer": cer_score
    }
    results.append(result)
    
    print(f"Sample {i+1}:")
    print(f"  Ground Truth: {transcript}")
    print(f"  Predicted:    {predicted_text}")
    print(f"  WER: {wer_score:.4f}, CER: {cer_score:.4f}\n")


average_wer = sum(wer_scores) / num_samples
average_cer = sum(cer_scores) / num_samples

results.append({
    "sample": "average",
    "wer": average_wer,
    "cer": average_cer
})

with open(result_file, "w") as f:
    for result in results:
        f.write(json.dumps(result) + "\n")

print(f"Average WER: {average_wer:.4f}")
print(f"Average CER: {average_cer:.4f}")