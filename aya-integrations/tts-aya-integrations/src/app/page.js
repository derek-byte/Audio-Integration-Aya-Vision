'use client';
//import Image from "next/image";
// import styles from "./page.module.css";
import { useState, useRef, useEffect } from 'react';
import { AudioRecorderWithVisualizer } from '@/components/AudioRecorderWithVisualizer';
import ChatInterface from '@/components/ChatInterface';
import Image from 'next/image';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import CameraCapture from '@/components/CameraCapture';

export default function Home() {
  const [inputText, setInputText] = useState('');
  const [outputText, setOutputText] = useState('');
  const [audioUrl, setAudioUrl] = useState('');
  const [selectVision, setSelectVision] = useState(false);
  const [uploadedImage, setUploadedImage] = useState(null);
  const fileInputRef = useRef(null);
  const [capturedImage, setCapturedImage] = useState(null);
  const [showCamera, setShowCamera] = useState(false);
  
  
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
    <div className="min-h-screen bg-white">
      {/* header start */}
      <header className="mb-8">
        <h1 className="mt-[50px] text-[32px] font-bold leading-[100%] text-center text-ayaBlack font-inter">Welcome to Aya Vision</h1>
        {/* <p className="text-center text-gray-600">Speech-to-Text and Text-to-Speech with AYA Vision</p> */}
      </header>

      <div className="m-auto w-3/5">
        <ChatInterface/>
      </div>

      <AudioRecorderWithVisualizer className="my-12 w-full max-w-full" />
      <div className="flex justify-center bg-gray-100 mt-[450px]">
      <div className="flex items-center justify-between bg-black text-white rounded-full px-4 py-2 w-[504px] h-[36px]">
        {/* Input wrapper */}
        <div className="flex-grow">
          <input
            type="text"
            className="bg-transparent outline-none w-full text-white placeholder-gray-400 flex-grow mr-3"
            placeholder="Text input..."
          />
        </div>

        {/* Send button wrapper */}
        <button className="ml-auto relative w-7 h-7 translate-x-2">
          {/* Grey Circle */}
          <Image
            src="/images/send_text_button_background.svg"
            alt="circle"
            fill
            className="absolute"
          />

          {/* Arrow (centered & smaller) */}
          <div className="absolute inset-0 flex items-center justify-center">
            <Image
              src="/images/sent_text_button_arrow.svg"
              alt="arrow"
              width={14}
              height={14}
            />
          </div>
        </button>
      </div>
      <div className="flex space-x-1 ml-1">
        <button className="flex items-center justify-center bg-black text-white rounded-full w-[35px] h-[35px]">
          <Image
            src="/images/mic_icon.svg"
            alt="mic"
            width={20}
            height={20}
          />
        </button>

{/* 
        {selectVision && (  */}
          <DropdownMenu open={selectVision} onOpenChange={setSelectVision}>
            <DropdownMenuTrigger asChild>
              <button
                className="flex items-center justify-center bg-black text-white rounded-full w-[35px] h-[35px]"
              >
                <Image
                  src="/images/camera_icon.svg"
                  alt="camera"
                  width={20}
                  height={20}
                />
              </button>
            </DropdownMenuTrigger>
            <DropdownMenuContent>
              {/* <DropdownMenuSeparator /> */}
              <DropdownMenuItem
               onClick={()=> triggerImageUpload()}
              >Upload Image</DropdownMenuItem>
              <DropdownMenuItem
               onClick={()=> setShowCamera(true)}>
                Camera</DropdownMenuItem>  
            </DropdownMenuContent>
          </DropdownMenu>
        {/* )} */}
      </div>
    </div>
    <input 
      type="file" 
      ref={fileInputRef}
      className="hidden"
      accept="image/*"
      onChange={handleImageUpload}
    />
    {showCamera && (
        <CameraCapture
          onCapture={(imageData) => setCapturedImage(imageData)}
          onClose={() => setShowCamera(false)}
        />
      )}

      {capturedImage && (
        <div className="mt-4">
          <img src={capturedImage} alt="Captured" className="max-w-md rounded" />
          <button onClick={() => setCapturedImage(null)} className="mt-2 px-4 py-2 bg-gray-600 text-white rounded">Retake</button>
        </div>
      )}

      {/* header end */}
      

    </div>
  );
}



