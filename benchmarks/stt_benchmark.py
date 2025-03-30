import torchaudio
import torchaudio.datasets as datasets
from FAdam.fadam import FAdam
from jiwer import wer, cer
import torch

import json
from tqdm import tqdm 


model = FAdam()
model.eval()

# Function to transcribe audio using FAdam
def fadam_stt_model(audio_waveform, sample_rate):
    """Convert waveform to text using the FAdam model."""
    # Resample if necessary (assuming FAdam uses 16kHz sample rate)
    if sample_rate != 16000:
        audio_waveform = torchaudio.transforms.Resample(sample_rate, 16000)(audio_waveform)

    # Process the waveform with FAdam
    with torch.no_grad():
        predicted_text = model(audio_waveform.squeeze().unsqueeze(0))  # Assuming the model's forward pass works like this
    return predicted_text

test_set = datasets.LIBRISPEECH("./data", url="test-clean", download=True)
result_file = "stt_benchmark_results.jsonl" # Adjust as needed

num_samples = 10  # Adjust as needed
wer_scores, cer_scores = [], []
results = []

for i in tqdm(range(num_samples), desc="Processing samples", unit="sample"):
    waveform, sample_rate, transcript, _, _, _ = test_set[i]
    
    predicted_text = fadam_stt_model(waveform, sample_rate)
    
    wer_score = wer(transcript.lower(), predicted_text.lower())
    cer_score = cer(transcript.lower(), predicted_text.lower())
    
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