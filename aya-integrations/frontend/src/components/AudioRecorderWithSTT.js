"use client";
import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Button } from "@/components/ui/button";
import { Mic, Send, Trash } from "lucide-react";
import { useTheme } from "next-themes";
import { cn } from "@/lib/utils";

let recorder;
let recordingChunks = [];
let timerTimeout;

// Utility function to pad a number with leading zeros
const padWithLeadingZeros = (num, length) => {
  return String(num).padStart(length, "0");
};

export const AudioRecorderWithSTT = ({
  className,
  timerClassName,
  onTranscriptionComplete,
  onClose,
}) => {
  const { theme } = useTheme();
  // States
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [timer, setTimer] = useState(0);
  const [transcript, setTranscript] = useState("");
  
  // Calculate the hours, minutes, and seconds from the timer
  const hours = Math.floor(timer / 3600);
  const minutes = Math.floor((timer % 3600) / 60);
  const seconds = timer % 60;

  // Split the hours, minutes, and seconds into individual digits
  const [hourLeft, hourRight] = useMemo(
    () => padWithLeadingZeros(hours, 2).split(""),
    [hours]
  );
  const [minuteLeft, minuteRight] = useMemo(
    () => padWithLeadingZeros(minutes, 2).split(""),
    [minutes]
  );
  const [secondLeft, secondRight] = useMemo(
    () => padWithLeadingZeros(seconds, 2).split(""),
    [seconds]
  );
  
  // Refs
  const mediaRecorderRef = useRef({
    stream: null,
    analyser: null,
    mediaRecorder: null,
    audioContext: null,
  });
  const canvasRef = useRef(null);
  const animationRef = useRef(null);

  // Speech recognition setup
  const recognitionRef = useRef(null);

  useEffect(() => {
    // Set up speech recognition if supported by the browser
    if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      recognitionRef.current = new SpeechRecognition();
      recognitionRef.current.continuous = true;
      recognitionRef.current.interimResults = true;
      
      recognitionRef.current.onresult = (event) => {
        let interimTranscript = '';
        let finalTranscript = '';
        
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            finalTranscript += event.results[i][0].transcript;
          } else {
            interimTranscript += event.results[i][0].transcript;
          }
        }
        
        setTranscript(finalTranscript || interimTranscript);
      };
      
      recognitionRef.current.onerror = (event) => {
        console.error('Speech recognition error', event.error);
      };
    }
    
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.stop();
      }
    };
  }, []);

  function startRecording() {
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      setTranscript("");
      navigator.mediaDevices
        .getUserMedia({
          audio: true,
        })
        .then((stream) => {
          setIsRecording(true);
          // Start speech recognition
          if (recognitionRef.current) {
            recognitionRef.current.start();
          }
          
          // ============ Analyzing ============
          const AudioContext = window.AudioContext || window.webkitAudioContext;
          const audioCtx = new AudioContext();
          const analyser = audioCtx.createAnalyser();
          const source = audioCtx.createMediaStreamSource(stream);
          source.connect(analyser);
          mediaRecorderRef.current = {
            stream,
            analyser,
            mediaRecorder: null,
            audioContext: audioCtx,
          };

          const mimeType = MediaRecorder.isTypeSupported("audio/mpeg")
            ? "audio/mpeg"
            : MediaRecorder.isTypeSupported("audio/webm")
            ? "audio/webm"
            : "audio/wav";

          const options = { mimeType };
          mediaRecorderRef.current.mediaRecorder = new MediaRecorder(
            stream,
            options
          );
          mediaRecorderRef.current.mediaRecorder.start();
          recordingChunks = [];
          // ============ Recording ============
          recorder = new MediaRecorder(stream);
          recorder.start();
          recorder.ondataavailable = (e) => {
            recordingChunks.push(e.data);
          };
        })
        .catch((error) => {
          alert("Microphone access error: " + error.message);
          console.log(error);
        });
    } else {
      alert("Your browser doesn't support microphone access.");
    }
  }
  
  function stopRecording() {
    setIsProcessing(true);
    
    // Stop speech recognition
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
    
    // Stop the media recorder
    if (recorder && recorder.state !== 'inactive') {
      recorder.stop();
    }
    
    // Stop all tracks in the stream
    const { stream } = mediaRecorderRef.current;
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
    }
    
    // Clean up the audio context
    const { audioContext, analyser } = mediaRecorderRef.current;
    if (analyser) {
      analyser.disconnect();
    }
    if (audioContext && audioContext.state !== 'closed') {
      audioContext.close();
    }
    
    setIsRecording(false);
    setTimer(0);
    clearTimeout(timerTimeout);
    
    // Complete the transcription process
    setTimeout(() => {
      onTranscriptionComplete(transcript);
      setIsProcessing(false);
      onClose();
    }, 500);
  }
  
  function resetRecording() {
    // Stop speech recognition
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
    
    const { mediaRecorder, stream, analyser, audioContext } = mediaRecorderRef.current;

    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
    }

    // Stop the web audio context and the analyser node
    if (analyser) {
      analyser.disconnect();
    }
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
    }
    if (audioContext && audioContext.state !== 'closed') {
      audioContext.close();
    }
    
    setIsRecording(false);
    setTranscript("");
    setTimer(0);
    clearTimeout(timerTimeout);

    // Clear the animation frame and canvas
    cancelAnimationFrame(animationRef.current || 0);
    const canvas = canvasRef.current;
    if (canvas) {
      const canvasCtx = canvas.getContext("2d");
      if (canvasCtx) {
        const WIDTH = canvas.width;
        const HEIGHT = canvas.height;
        canvasCtx.clearRect(0, 0, WIDTH, HEIGHT);
      }
    }
    
    onClose();
  }

  // Effect to update the timer every second
  useEffect(() => {
    if (isRecording) {
      timerTimeout = setTimeout(() => {
        setTimer(timer + 1);
      }, 1000);
    }
    return () => clearTimeout(timerTimeout);
  }, [isRecording, timer]);

  // Visualizer
  useEffect(() => {
    if (!canvasRef.current) return;

    const canvas = canvasRef.current;
    const canvasCtx = canvas.getContext("2d");
    const WIDTH = canvas.width;
    const HEIGHT = canvas.height;

    const drawWaveform = (dataArray) => {
      if (!canvasCtx) return;
      canvasCtx.clearRect(0, 0, WIDTH, HEIGHT);
      canvasCtx.fillStyle = "#939393";

      const barWidth = 1;
      const spacing = 1;
      const maxBarHeight = HEIGHT / 2.5;
      const numBars = Math.floor(WIDTH / (barWidth + spacing));

      for (let i = 0; i < numBars; i++) {
        const barHeight = Math.pow(dataArray[i] / 128.0, 8) * maxBarHeight;
        const x = (barWidth + spacing) * i;
        const y = HEIGHT / 2 - barHeight / 2;
        canvasCtx.fillRect(x, y, barWidth, barHeight);
      }
    };

    const visualizeVolume = () => {
      if (
        !mediaRecorderRef.current?.stream?.getAudioTracks()[0]?.getSettings()
          .sampleRate
      )
        return;
      
      const analyser = mediaRecorderRef.current.analyser;
      if (!analyser) return;
      
      analyser.fftSize = 2048;
      const bufferLength = analyser.frequencyBinCount;
      const dataArray = new Uint8Array(bufferLength);

      const draw = () => {
        if (!isRecording) {
          cancelAnimationFrame(animationRef.current || 0);
          return;
        }
        
        animationRef.current = requestAnimationFrame(draw);
        analyser.getByteTimeDomainData(dataArray);
        drawWaveform(dataArray);
      };

      draw();
    };

    if (isRecording) {
      visualizeVolume();
    } else {
      if (canvasCtx) {
        canvasCtx.clearRect(0, 0, WIDTH, HEIGHT);
      }
      cancelAnimationFrame(animationRef.current || 0);
    }

    return () => {
      cancelAnimationFrame(animationRef.current || 0);
    };
  }, [isRecording, theme]);

  return (
    <div className="bg-white p-4 rounded-lg shadow-lg w-full max-w-md">
      <div className={cn(
        "flex flex-col items-center justify-center gap-4",
        className
      )}>
        {isRecording ? (
          <Timer
            hourLeft={hourLeft}
            hourRight={hourRight}
            minuteLeft={minuteLeft}
            minuteRight={minuteRight}
            secondLeft={secondLeft}
            secondRight={secondRight}
            timerClassName={timerClassName}
          />
        ) : null}
        
        {/* Transcript preview */}
        {transcript && (
          <div className="w-full bg-gray-50 p-3 rounded-md max-h-32 overflow-y-auto">
            <p className="text-sm text-gray-800">{transcript}</p>
          </div>
        )}
        
        {/* Audio visualizer */}
        <div className="w-full h-16 relative">
          <canvas
            ref={canvasRef}
            className={`h-full w-full bg-gray-100 rounded ${!isRecording ? "hidden" : "flex"}`}
            width="400"
            height="64"
          />
          {!isRecording && !transcript && (
            <div className="absolute inset-0 flex items-center justify-center text-gray-500 text-sm">
              Click the microphone to start recording
            </div>
          )}
        </div>
        
        {/* Controls */}
        <div className="flex gap-4 justify-center">
          {isRecording ? (
            <>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    onClick={resetRecording}
                    size="icon"
                    variant="destructive"
                    disabled={isProcessing}
                  >
                    <Trash size={18} />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Cancel recording</TooltipContent>
              </Tooltip>
              
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    onClick={stopRecording}
                    size="icon"
                    variant="default"
                    disabled={isProcessing}
                  >
                    <Send size={18} />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Send message</TooltipContent>
              </Tooltip>
            </>
          ) : (
            <>
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button 
                    onClick={startRecording} 
                    size="icon"
                    variant="default"
                    disabled={isProcessing}
                  >
                    <Mic size={18} />
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Start recording</TooltipContent>
              </Tooltip>
              
              {transcript && (
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      onClick={() => {
                        onTranscriptionComplete(transcript);
                        onClose();
                      }}
                      size="icon"
                      variant="default"
                      disabled={isProcessing}
                    >
                      <Send size={18} />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Send message</TooltipContent>
                </Tooltip>
              )}
              
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    onClick={onClose}
                    size="icon"
                    variant="outline"
                    disabled={isProcessing}
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="lucide lucide-x"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
                  </Button>
                </TooltipTrigger>
                <TooltipContent>Close</TooltipContent>
              </Tooltip>
            </>
          )}
        </div>
        
        {isProcessing && (
          <div className="text-sm text-gray-500">Processing...</div>
        )}
      </div>
    </div>
  );
};

const Timer = React.memo(
  ({
    hourLeft,
    hourRight,
    minuteLeft,
    minuteRight,
    secondLeft,
    secondRight,
    timerClassName,
  }) => {
    return (
      <div
        className={cn(
          "items-center justify-center gap-0.5 border p-1.5 rounded-md font-mono font-medium text-foreground flex",
          timerClassName
        )}
      >
        <span className="rounded-md bg-background p-0.5 text-foreground">
          {hourLeft}
        </span>
        <span className="rounded-md bg-background p-0.5 text-foreground">
          {hourRight}
        </span>
        <span>:</span>
        <span className="rounded-md bg-background p-0.5 text-foreground">
          {minuteLeft}
        </span>
        <span className="rounded-md bg-background p-0.5 text-foreground">
          {minuteRight}
        </span>
        <span>:</span>
        <span className="rounded-md bg-background p-0.5 text-foreground">
          {secondLeft}
        </span>
        <span className="rounded-md bg-background p-0.5 text-foreground ">
          {secondRight}
        </span>
      </div>
    );
  }
);
Timer.displayName = "Timer";