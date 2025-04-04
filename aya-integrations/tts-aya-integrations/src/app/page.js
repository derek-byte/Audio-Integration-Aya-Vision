'use client';
//import Image from "next/image";
// import styles from "./page.module.css";
import { useState, useRef, useEffect } from 'react';
import AudioRecorder from '../components/AudioRecorder';



export default function Home() {
  const [inputText, setInputText] = useState('');
  const [outputText, setOutputText] = useState('');
  const [audioUrl, setAudioUrl] = useState('');
  const [uploadedImage, setUploadedImage] = useState(null);
  const fileInputRef = useRef(null);
  
  // Handle text input changes
  const handleTextChange = (e) => {
    setInputText(e.target.value);
  };
  
  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    let base64Image = null
    if (fileInputRef.current.files[0]){
      const file = fileInputRef.current.files[0];
      const reader = new FileReader();
      base64Image = await new Promise((resolve, reject) => {
        reader.onloadend = () => resolve(reader.result);
        reader.onerror = reject;
        reader.readAsDataURL(file);
      });
    }

    // call api 
  try {
    const res = await fetch('/api/vision', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        message: inputText || "What do you see in this image?",
        base64Image,
      }),
    });

    const data = await res.json();
    console.log('🧠 Vision model response:', data);
    setOutputText(data.reply || "No reply from vision model.");
  } catch (err) {
    console.error("❌ API call failed:", err);
    setOutputText("Error: could not reach vision model.");
  }


    // Simulate response - in a real app, this would call your backend
    // setOutputText(`Response to: ${inputText}`);
    
    // // Simulate TTS - in a real app, this would generate actual audio
    setAudioUrl('https://example.com/audio.mp3');
    

    // Reset input
    setInputText('');
  };
  
  // Handle transcription from audio recorder
  const handleTranscription = (text) => {
    setInputText(text);
  };
  
  // Handle image upload
  const handleImageUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const imageUrl = URL.createObjectURL(file);
      setUploadedImage(imageUrl);
    }
  };
  
  // Trigger file input click
  const triggerImageUpload = () => {
    fileInputRef.current.click();
  };

  const speak = () => {
    if ("speechSynthesis" in window) {
      const utterance = new SpeechSynthesisUtterance(outputText);
      speechSynthesis.speak(utterance);
    } else {
      alert("Your browser does not support Text-to-Speech.");
    }
  };

  useEffect(() => {
    speak();
  }, [outputText]) // replace this later w/ audioURL;

  return (
    <div className="min-h-screen bg-gray-100 p-6">
      {/* header start */}
      <header className="mb-8">
      

        <h1 className="text-3xl font-bold text-center text-blue-600">AYA Vision Integration</h1>
        <p className="text-center text-gray-600">Speech-to-Text and Text-to-Speech with AYA Vision</p>
      </header>
      {/* header end */}
      <main className="max-w-4xl mx-auto bg-white rounded-xl shadow-md overflow-hidden">
        <div className="p-6 border-b">
          <div className="flex flex-col space-y-4">
            {/* Input Section */}
            <div className="border rounded-lg p-4">
              <div className="flex justify-between items-center mb-2">
                <h2 className="text-xl font-semibold">Input</h2>
                <div className="flex space-x-2">
                  <AudioRecorder onTranscription={handleTranscription} />
                  
                  <div className="relative">
                    <button 
                      onClick={triggerImageUpload}
                      className="px-4 py-2 bg-blue-600 text-white rounded"
                    >
                      UPLOAD IMAGE
                    </button>
                    <input 
                      type="file" 
                      ref={fileInputRef}
                      className="hidden"
                      accept="image/*"
                      onChange={handleImageUpload}
                    />
                  </div>
                </div>
              </div>
              
              {uploadedImage && (
                <div className="mb-4 border rounded p-2">
                  <img 
                    src={uploadedImage} 
                    alt="Uploaded" 
                    className="max-h-40 max-w-full mx-auto"
                  />
                </div>
              )}
              
              <form onSubmit={handleSubmit}>
                <textarea
                  value={inputText}
                  onChange={handleTextChange}
                  placeholder="Type here or use voice input..."
                  className="w-full h-32 p-2 border rounded resize-none"
                ></textarea>
                
                <div className="flex justify-end mt-2">
                  <button
                    type="submit"
                    className="px-4 py-2 bg-green-600 text-white rounded"
                  >
                    SEND
                  </button>
                </div>
              </form>
            </div>
            
            {/* Output Section */}
            <div className="border rounded-lg p-4">
              <h2 className="text-xl font-semibold mb-2">Output</h2>
              
              <div className="bg-gray-100 p-3 rounded min-h-32 mb-4">
                {outputText || 'Response will appear here...'}
              </div>
              
              {audioUrl && (
                <div className="flex justify-center">
                  <audio controls src={audioUrl} className="w-full">
                    Your browser does not support the audio element.
                  </audio>
                </div>
              )}
            </div>
          </div>
        </div>
        
        {/* System Information */}
        {/* <div className="p-6 bg-gray-50">
          <div className="flex justify-between">
            <div className="border rounded p-3 w-64">
              <h3 className="font-medium text-gray-700">Speech to Text Unit</h3>
              <p className="text-sm text-gray-500">Either in-browser or isolated</p>
            </div>
            
            <div className="border rounded p-3 w-64">
              <h3 className="font-medium text-gray-700">Text to Speech Unit</h3>
              <p className="text-sm text-gray-500">Either in-browser or isolated</p>
            </div>
            
            <div className="border rounded p-3 w-64">
              <h3 className="font-medium text-gray-700">AYA VISION 8B/32B</h3>
              <p className="text-sm text-gray-500">Processing vision and text data</p>
            </div>
          </div>
        </div> */}
      </main>
    </div>
  );
}
