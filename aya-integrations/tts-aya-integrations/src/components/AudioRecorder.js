'use client';

import { useState, useEffect, useRef } from 'react';

export default function AudioRecorder({ onTranscription }) {
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const timerRef = useRef(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    };
  }, []);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      
      mediaRecorderRef.current.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };
      
      mediaRecorderRef.current.onstop = () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        const audioUrl = URL.createObjectURL(audioBlob);
        
        // In a real app, you'd send this blob to your STT service
        // For now, we'll just simulate a transcription
        setTimeout(() => {
          onTranscription("This is simulated text from the speech recognition service.");
        }, 1000);
        
        // Reset recording time and chunks
        setRecordingTime(0);
        audioChunksRef.current = [];
      };
      
      mediaRecorderRef.current.start();
      setIsRecording(true);
      
      // Start timer
      timerRef.current = setInterval(() => {
        setRecordingTime((prevTime) => prevTime + 1);
      }, 1000);
      
    } catch (error) {
      console.error('Error accessing microphone:', error);
    }
  };
  
  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
      setIsRecording(false);
      
      if (timerRef.current) {
        clearInterval(timerRef.current);
      }
    }
  };
  
  const toggleRecording = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };
  
  // Format time as mm:ss
  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60).toString().padStart(2, '0');
    const secs = (seconds % 60).toString().padStart(2, '0');
    return `${mins}:${secs}`;
  };
  
  return (
    <div className="flex items-center space-x-2">
      <button 
        onClick={toggleRecording}
        className={`p-3 rounded-full flex items-center justify-center ${isRecording ? 'bg-red-500 text-white' : 'bg-gray-200'}`}
        title={isRecording ? "Stop Recording" : "Start Recording"}
      >
        <div className={`w-3 h-3 rounded-full ${isRecording ? 'animate-pulse bg-white' : 'bg-red-500'}`}></div>
      </button>
      
      {isRecording && (
        <div className="text-sm font-mono">{formatTime(recordingTime)}</div>
      )}
    </div>
  );
}