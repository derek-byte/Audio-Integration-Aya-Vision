// src/app/speech-to-text/page.js
"use client";

import { useState } from 'react';
import AudioRecorder from '@/components/speech/AudioRecorder';

export default function SpeechToTextPage() {
  const [transcript, setTranscript] = useState('');

  const resetTranscript = () => {
    setTranscript('');
  };

  return (
    <div className="max-w-2xl mx-auto p-6">
      <h1 className="text-2xl font-bold mb-6">Speech to Text</h1>
      
      <AudioRecorder 
        onTranscriptionUpdate={setTranscript} 
        initialTranscript=""
      />
      
      <div className="border rounded-lg p-4 min-h-32 bg-gray-50 mb-4">
        <div className="flex justify-between items-center mb-2">
          <h2 className="font-semibold">Transcript:</h2>
          {transcript && (
            <button 
              onClick={resetTranscript}
              className="text-xs px-2 py-1 bg-gray-200 rounded hover:bg-gray-300"
            >
              Clear
            </button>
          )}
        </div>
        <p className="whitespace-pre-wrap">{transcript || 'No transcript yet. Start speaking after pressing record.'}</p>
      </div>
    </div>
  );
}