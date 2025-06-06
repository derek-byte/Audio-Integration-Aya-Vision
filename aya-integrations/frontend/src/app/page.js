'use client';
//import Image from "next/image";
// import styles from "./page.module.css";
import { useState, useRef, useEffect } from 'react';
import ChatInterface from '@/components/ChatInterface';
import { ReactTyped } from 'react-typed';

export default function Home() {
  const [inputText, setInputText] = useState('');
  const [outputText, setOutputText] = useState('');
  const fileInputRef = useRef(null);
  
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
    <div className="min-h-screen bg-white">
      {/* header start */}
      <header className="mb-4 my-12 mx-auto flex items-center justify-center">
      <div className="text-xl font-mono py-2 px-6">
        <ReactTyped
          strings={["const vision = \"aya vision\";"]}
          typeSpeed={100}
          backSpeed={50}
          // loop
          showCursor
        />
      </div>
  {/* <p className="text-center text-gray-600">Speech-to-Text and Text-to-Speech with AYA Vision</p> */}
</header>


      <div className="m-auto w-full max-w-3xl">
        <ChatInterface/>
      </div>
    </div>
  );
}



