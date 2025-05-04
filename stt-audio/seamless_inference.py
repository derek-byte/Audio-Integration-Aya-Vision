
### This code is a modified copy from https://github.com/facebookresearch/seamless_communication/blob/main/Seamless_Tutorial.ipynb

import numpy as np
import torchaudio
import torch
import queue
import math
import logging

from typing import Union, List
from simuleval import options
from simuleval.utils.arguments import cli_argument_list
from simuleval.data.segments import Segment, TextSegment, SpeechSegment
from seamless_communication.streaming.agents.seamless_streaming_s2t import SeamlessStreamingS2TVADAgent

MODEL_SAMPLE_RATE_HERTZ = 16000
TASK="s2tt"


class AudioFrontEnd:

    def __init__(self, segment_size_ms = 1) -> None:
        """ This class is responsible for loading, preprocessing, storing input audio data to be provided to inference system at a later stage.
        During inference, the inference system will keep calling send_segment to get a new segment of audio data.

        Args:
            segment_size_ms: size in milliseconds of the audio segment to be provided to the inference system.
        """
        self.input_queue = queue.Queue() # queue to store input data before providing it to the inference system
        self.segment_size_ms = segment_size_ms
    
    def put_audio_data_from_file(self, file_path: str, **kwargs):
        """ function reads audio data from file and stores it in the input queue 
        Args:
            file_path: path to input file
            kwargs: kwargs to read the input file
        """
        import soundfile as sf
        data, sample_rate = sf.read(file_path, **kwargs)
        self.put_audio_data(input_sample_rate=sample_rate, input_audio_data=data)
    
    @staticmethod
    def is_stereo_data(data: np.array):
        """ function check if the provided data is stereo audio """
        return (data.ndim == 2) and (data.shape[1] == 2)
        
    def put_audio_data(self, input_sample_rate: int, input_audio_data: np.array):
        """ function adds input data to the input queue

        Args:
            input_sample_rate: sample rate (frequency) of the input audio data
            input_audio_data: np array holding audio data
        
        """

        if self.is_stereo_data(input_audio_data):
            input_audio_data = np.mean(input_audio_data, axis=1)

        assert input_audio_data.ndim == 1

        assert self.segment_size_ms is not None

        segment_size_samples = math.ceil(self.segment_size_ms / 1000 * input_sample_rate)
        audio_input_length = input_audio_data.shape[0]

        # if the size of input data is the expected size of 1 segment, add it directly to the queue
        if segment_size_samples == audio_input_length:
            self.input_queue.put_nowait((input_sample_rate, input_audio_data))

        # if the size of the input data is smaller than the size of 1 segment, pad it with zeros, then add it to the queue
        elif segment_size_samples > audio_input_length:
            pad_size = segment_size_samples - audio_input_length
            input_audio_data = np.pad(input_audio_data, (0, pad_size), 'constant', constant_values=0)
            self.input_queue.put_nowait((input_sample_rate, input_audio_data))

        else:
            # this should be the normal case
            # if the size of the input data is greater than the size of 1 segment, 
            #   pad it with zeros so that it is divisible by the size of the segment
            #   add each segment to the input queue

            num_splits, remainder = divmod(audio_input_length, segment_size_samples)

            # division has a remainder -> indicating that padding is needed to complete the last segment
            if remainder > 0:
                pad_size = segment_size_samples - remainder
                input_audio_data = np.pad(input_audio_data, (0, pad_size), 'constant', constant_values=0)
                num_splits = num_splits + 1
            
            # split the data into segments and add it to the queue
            audio_segments = np.split(input_audio_data, indices_or_sections=num_splits)
            for s in audio_segments:
                self.input_queue.put_nowait((input_sample_rate, s))
                
    
    def send_segment(self):
        """ main function that is called every time by the inference system to get new data"""
        segment = None

        # check if input queue is empty
        if not self.input_queue.empty():
            sample_rate, samples = self.input_queue.get()

            # downsample the sample rate of the input data to the one expected by the inference system
            if sample_rate > MODEL_SAMPLE_RATE_HERTZ:
                samples = torchaudio.functional.resample(torch.from_numpy(samples), orig_freq=sample_rate, new_freq=MODEL_SAMPLE_RATE_HERTZ).numpy()
                sample_rate = MODEL_SAMPLE_RATE_HERTZ
            
            assert sample_rate == MODEL_SAMPLE_RATE_HERTZ, f"sample rate of input data {sample_rate} does not match the sample rate expected by the inference engine {MODEL_SAMPLE_RATE_HERTZ}"

            # create a speech segment from the audio data
            segment = SpeechSegment(
                    content=samples,
                    sample_rate=sample_rate,
                    finished=False,
                    is_empty=False
                )
        
        else:
            # if the input queue is empty, provide a speech segment with zeros
            silence_segment_size = math.ceil(self.segment_size_ms / 1000 * MODEL_SAMPLE_RATE_HERTZ)
            segment = SpeechSegment(
                content=np.zeros(silence_segment_size),
                sample_rate=MODEL_SAMPLE_RATE_HERTZ,
                finished=True, # indicate that the input data is finished
                is_empty=True  # indicate that the speech segment has invalid data
            ) 
        
        return segment


class OutputSegments:
    """container class that will host the output segments from the inference system """
    def __init__(self, segments: Union[List[Segment], Segment]):
        if isinstance(segments, Segment):
            segments = [segments]
        self.segments: List[Segment] = [s for s in segments]

    @property
    def is_empty(self):
        return all(segment.is_empty for segment in self.segments)

    @property
    def finished(self):
        return all(segment.finished for segment in self.segments)

class SeamlessStreamingWrapper(object):

    def __init__(self, model_config: dict, audio_frontend: AudioFrontEnd, tgt_lang: str = "eng"):
        """ This is a wrapper class used to run the seamless streaming model. It is the primary class used for inference.
        It wraps the SeamlessStreamingS2TVADAgent from seamless_communication library. SeamlessStreamingS2TVADAgent is the seamless streaming inference system. It has 5 stages which are run in pipeline to produce the output segments

        - SileroVADAgent -> Silero VAD model which is used for voice activity detection
        - OnlineFeatureExtractorAgent -> feature extraction model that converts audio waveform into features, includes WaveformToFbankConverter
        - OfflineWav2VecBertEncoderAgent -> Bert model that encodes the input features for various down stream tasks 
        - MMASpeechToTextDecoderAgent -> model that converts encodings into text tokens
        - DetokenizerAgent -> final stage that convert the text tokens into text (output segments)

        Args:
            model_config: dictionary with seamless model configuration that will be used to create an instance of seamless inference system.
            audio_frontend: frontend use to retrive input data
            tgt_lang: target language to translate the input audio to.
        
        """

        #  seamless system used for inference
        self._system =  self.build_system_from_config(model_config)

        # seamless system states used during inference
        self._system_states = self._system.build_states()

        # audio frontend to get input data from
        self._audio_frontend = audio_frontend

        # target language fro translation
        self.tgt_lang = tgt_lang

    @staticmethod
    def reset_states(states):
        """ reset the states used in the inference system"""
        states_iter = states
        for state in states_iter:
            state.reset()
    
    def build_system_from_config(self, model_config: dict):
        """ build the inference system using the provided config. 
        Each of the five stages of the inference system takes its configuration parameters in the form of parser arguments. 
        Check "add_args" function in source code of the 5 stages' classes to learn more about the parameters that you can add to model_config.

        Example:
            SileroVADAgent class in the seamless_communication package has an add_args method. It shows the arguments expected by the model 
            such as: window-size-samples, chunk-size-samples, silence-limit-ms, speech-soft-limit-m, init-speech-prob, debug
            to set any of those parameters, you can use the model config. model_config["silence_limit_ms"] = 100
        """
        parser = options.general_parser()
        SeamlessStreamingS2TVADAgent.add_args(parser)
        args, _ = parser.parse_known_args(cli_argument_list(model_config))
        system = SeamlessStreamingS2TVADAgent.from_args(args)
        return system


    def _run_inference_pipeline(self, return_partial_predictions: bool = False) -> Union[str, List[str]]:
        """ This is primary function used for inference. It takes input from the audio_frontend and produces the predicted text
        
        Args:
            return_partial_predictions: return the partial predictions produced by the model instead of one combined single text
        """
        # list of predicted texts
        prediction_lists: List[str] = []

        # current delay, variable only used for display purposes
        curr_delay = 0

        while True:
            # read data from front end
            input_segment = self._audio_frontend.send_segment()
            # set target language
            input_segment.tgt_lang = self.tgt_lang
            curr_delay += len(input_segment.content) / MODEL_SAMPLE_RATE_HERTZ * 1000
            # if audio_frontend finished producing data, indicate this to inference system
            if input_segment.finished:
                self._system_states[0].source_finished = True

            # Run inference sysetem
            output_segments = OutputSegments(self._system.pushpop(input_segment, self._system_states))

            # if output segments are produces
            if not output_segments.is_empty:
                for segment in output_segments.segments:
                    # check if each segment has text
                    if isinstance(segment, TextSegment):
                        # add text to the predicted texts and print also print it.
                        prediction_lists.append(segment.content)
                        # logging.info(f"{curr_delay} {segment.content}")
            
            # if the system finished producing output for the provided input, reset it states
            if output_segments.finished:
                self.reset_states(self._system_states)
            
            # if audio_frontend finished producing input data, and inference system finished producing output, break
            if input_segment.finished and output_segments.finished:
                # once source_finished=True, generate until output translation is finished
                break

        if return_partial_predictions:
            return prediction_lists
        
        else:
            text = " ".join(prediction_lists)

        return text
    

    def run_inference(self, input_sample_rate: int, input_audio_data: np.array, return_partial_predictions: bool = False):
        """ run inference on the provided data sample """
        self._audio_frontend.put_audio_data(input_sample_rate=input_sample_rate, 
                                                input_audio_data=input_audio_data)
        preds = self._run_inference_pipeline(return_partial_predictions) 
        
        return preds
    
    def transcribe_file(self, file_path, return_partial_predictions: bool = False):
        """ run inference on the audio data provided in the file """
        self._audio_frontend.put_audio_data_from_file(file_path=file_path)
        preds = self._run_inference_pipeline(return_partial_predictions)
        return preds

def get_seamless_default_config() -> dict:
    tgt_lang = "eng"
    source_segment_size_ms = 1000   # milliseconds # size of audio segment to provided for inference each time.
    silence_limit_ms = 320 # milliseconds # SileroVADAgent produces EOS after this amount of silence.
    device = "cuda" if torch.cuda.is_available() else "cpu"
    decision_threshold = 0.5 # probability threshold for detecting speech / voice activtiy

    model_config = dict(
        source_segment_size=source_segment_size_ms,
        silence_limit_ms=silence_limit_ms,
        device=device,
        decision_threshold=decision_threshold,
        task=TASK,
        tgt_lang=tgt_lang,
    )

    return model_config

def load_model(model_config: dict) -> SeamlessStreamingWrapper:
    audio_frontend = AudioFrontEnd(segment_size_ms=model_config["source_segment_size"])
    wrapper = SeamlessStreamingWrapper(model_config=model_config, audio_frontend=audio_frontend, tgt_lang=model_config["tgt_lang"])
    return wrapper

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Seamless Inference")
    parser.add_argument("audio", help="Path to audio file")

    args = parser.parse_args()

    model_config = get_seamless_default_config()
    model_config["device"] = "cpu"
    wrapper = load_model(model_config=model_config)
    text = wrapper.transcribe_file(
        file_path=args.audio
    )
    print(text)

    # import gradio  as gr
    # def gradio_callback(stream, new_chunk):
    #     text = None
    #     if new_chunk is not None:
    #         sr, y = new_chunk
    #         text = adaptor.run_inference(input_sample_rate=sr, input_audio_data=y)
    #     return stream, text


    # with gr.Interface(
    #     gradio_callback,
    #     ["state", gr.Audio(
    #         sources=["upload"], 
    #         streaming=False,
    #         waveform_options=gr.WaveformOptions(sample_rate=MODEL_SAMPLE_RATE))],
    #     ["state", "text"],
    #     live=False,
    # ) as demo:
    #     demo.launch()
    