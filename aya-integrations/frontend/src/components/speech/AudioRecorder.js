// components/speech/AudioRecorder.jsx
"use client";

import { useState, useRef, useEffect } from 'react';

export default function AudioRecorder({ 
  onTranscriptionUpdate,
  initialTranscript = "" 
}) {
  const [isRecording, setIsRecording] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const socketRef = useRef(null);

  // Initialize websocket connection
  useEffect(() => {
    // Connect to your Flask backend websocket
    socketRef.current = new WebSocket('ws://localhost:5000/stream-audio');
    
    socketRef.current.onopen = () => {
      console.log('WebSocket connection established');
    };
    
    socketRef.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.transcription) {
        onTranscriptionUpdate(prev => prev + ' ' + data.transcription);
      }
    };
    
    socketRef.current.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
    
    socketRef.current.onclose = () => {
      console.log('WebSocket connection closed');
    };
    
    return () => {
      if (socketRef.current) {
        socketRef.current.close();
      }
    };
  }, [onTranscriptionUpdate]);

  const startRecording = async () => {
    try {
      setIsLoading(true);
      
      // Get audio stream from user's microphone
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      
      // Create MediaRecorder instance
      // const mediaRecorder = new MediaRecorder(stream, {
      //   mimeType: 'audio/webm',
      // });
      let mimeType = '';
      if (MediaRecorder.isTypeSupported('audio/webm')) {
        mimeType = 'audio/webm';
      } else if (MediaRecorder.isTypeSupported('audio/ogg')) {
        mimeType = 'audio/ogg';
      } else if (MediaRecorder.isTypeSupported('audio/wav')) {
        mimeType = 'audio/wav';
      }

      const audioContext = new AudioContext({ sampleRate: 16000 });
      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      
      mediaRecorderRef.current = { stream, audioContext, processor };
      
      processor.onaudioprocess = (e) => {
        const input = e.inputBuffer.getChannelData(0);
        const int16Buffer = new Int16Array(input.length);
      
        for (let i = 0; i < input.length; i++) {
          let s = Math.max(-1, Math.min(1, input[i]));
          int16Buffer[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
      
        const blob = new Blob([int16Buffer.buffer], { type: "application/octet-stream" });
            const reader = new FileReader();
            reader.onloadend = () => {
          const base64data = reader.result.split(",")[1];
          if (socketRef.current?.readyState === WebSocket.OPEN) {
            socketRef.current.send(JSON.stringify({ audio_data: base64data }));
          }
            };
        reader.readAsDataURL(blob);
      };
      
      source.connect(processor);
      processor.connect(audioContext.destination);
      
      setIsRecording(true);
      setIsLoading(false);
    } catch (error) {
      console.error('Error starting recording:', error);
      setIsLoading(false);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      const { stream, audioContext, processor } = mediaRecorderRef.current;
      
      processor?.disconnect();
      stream?.getTracks().forEach((track) => track.stop());
      audioContext?.close();
      
      setIsRecording(false);
    }
    
  };

  return (
    <div className="mb-6">
      <div className="flex justify-center space-x-4 mb-4">
        {!isRecording ? (
          <button
            onClick={startRecording}
            disabled={isLoading}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 disabled:bg-blue-300"
          >
            {isLoading ? 'Initializing...' : 'Start Recording'}
          </button>
        ) : (
          <button
            onClick={stopRecording}
            className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
          >
            Stop Recording
          </button>
        )}
      </div>
      
      {isRecording && (
        <div className="text-center text-sm text-red-500">
          Recording in progress...
        </div>
      )}
    </div>
  );
}