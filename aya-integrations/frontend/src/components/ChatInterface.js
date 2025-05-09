"use client";

import React, { useState, useRef, useEffect, useMemo } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Mic, Camera, Send, Square, Loader2, Volume2, VolumeX, Settings } from "lucide-react";
import CameraCapture from "./CameraCapture"; 
import { cn } from "@/lib/utils";
import { useTheme } from "next-themes";
import { 
  getAyaResponse, 
  streamAudioForTranscription, 
  playResponseAudio, 
  getAvailableModels,
  setTranscriptionModel
} from "../lib/api";

// Import shadcn Drawer components
import {
  Drawer,
  DrawerClose,
  DrawerContent,
  DrawerDescription,
  DrawerFooter,
  DrawerHeader,
  DrawerTitle,
  DrawerTrigger,
} from "@/components/ui/drawer";

export default function ChatInterface() {
  const [messages, setMessages] = useState([
    {
      isBot: true,
      content:
        "I'm Aya Vision, a large language model, or an artificial intelligence, if you prefer. I was created by Cohere Labs to help you in many different ways, from drafting messages and performing tasks to generating and analyzing images. You can also talk to me about something serious or just have a fun conversation. Whatever is on your mind, I'm here for you.\n\nWhat can I do for you?",
    },
  ]);
  const [input, setInput] = useState("");
  const [showCamera, setShowCamera] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [capturedImage, setCapturedImage] = useState(null);
  const [transcript, setTranscript] = useState("");
  const [timer, setTimer] = useState(0);
  const [isProcessing, setIsProcessing] = useState(false);
  const [audioEnabled, setAudioEnabled] = useState(true); // For TTS toggle
  const [currentAudio, setCurrentAudio] = useState(null); // Track current audio player
  
  // Model selection states
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [availableModels, setAvailableModels] = useState([]);
  const [currentModel, setCurrentModel] = useState("");
  const [loadingModels, setLoadingModels] = useState(false);
  
  const messagesEndRef = useRef(null);
  const messageContainerRef = useRef(null);
  const canvasRef = useRef(null);
  const animationRef = useRef(null);
  const { theme } = useTheme();
  
  // WebSocket ref for streaming audio
  const webSocketRef = useRef(null);
  
  // Audio recording references
  const mediaRecorderRef = useRef({
    stream: null,
    analyser: null,
    mediaRecorder: null,
    audioContext: null,
  });
  const recognitionRef = useRef(null);
  const timerIntervalRef = useRef(null);
  
  // Audio chunks for recording
  const audioChunksRef = useRef([]);
  
  // Timer formatting
  const hours = Math.floor(timer / 3600);
  const minutes = Math.floor((timer % 3600) / 60);
  const seconds = timer % 60;

  // Split the hours, minutes, and seconds into individual digits
  const [hourLeft, hourRight] = useMemo(
    () => String(hours).padStart(2, "0").split(""),
    [hours]
  );
  const [minuteLeft, minuteRight] = useMemo(
    () => String(minutes).padStart(2, "0").split(""),
    [minutes]
  );
  const [secondLeft, secondRight] = useMemo(
    () => String(seconds).padStart(2, "0").split(""),
    [seconds]
  );

  // Fetch available models on component mount
  useEffect(() => {
    fetchAvailableModels();
  }, []);

  // Function to fetch available transcription models
  const fetchAvailableModels = async () => {
    try {
      setLoadingModels(true);
      const modelData = await getAvailableModels();
      setAvailableModels(modelData.models || []);
      setCurrentModel(modelData.current_model || "faster_whisper");
      setLoadingModels(false);
    } catch (error) {
      console.error("Error fetching models:", error);
      setLoadingModels(false);
    }
  };

  // Function to change the active transcription model
  const handleModelChange = async (modelName) => {
    try {
      setLoadingModels(true);
      const result = await setTranscriptionModel(modelName);
      if (result.success) {
        setCurrentModel(modelName);
        // Add system message about model change
        setMessages(prev => [
          ...prev,
          {
            isBot: true,
            content: `Transcription model changed to ${modelName}.`
          }
        ]);
      }
      setLoadingModels(false);
      setDrawerOpen(false); // Close drawer after changing model
    } catch (error) {
      console.error("Error changing model:", error);
      setLoadingModels(false);
    }
  };

  // Setup speech recognition
  useEffect(() => {
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

  // Function to format messages for the API
  const formatMessagesForApi = () => {
    return messages.map(msg => ({
      content: msg.content,
      isBot: msg.isBot,
      image: msg.image || null
    }));
  };

  // Stop any playing audio when component unmounts
  useEffect(() => {
    return () => {
      if (currentAudio) {
        currentAudio.pause();
        currentAudio.src = '';
      }
    };
  }, []);

  // Base64 encode image from camera
  const getBase64FromImageUrl = async (imageUrl) => {
    try {
      if (!imageUrl) return null;
      
      // Fetch the image and convert to blob
      const response = await fetch(imageUrl);
      const blob = await response.blob();
      
      // Read the blob as Data URL (base64)
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onloadend = () => {
          // Extract the base64 part from the Data URL
          const base64String = reader.result.split(',')[1];
          resolve(base64String);
        };
        reader.onerror = reject;
        reader.readAsDataURL(blob);
      });
    } catch (error) {
      console.error("Error converting image to base64:", error);
      return null;
    }
  };

  const handleSendMessage = async (e) => {
    e?.preventDefault();
    if ((input.trim() === "" && transcript.trim() === "") && !capturedImage) return;
    
    const messageContent = input || transcript;
    
    // Process image if available
    let base64Image = null;
    if (capturedImage) {
      base64Image = await getBase64FromImageUrl(capturedImage);
    }
    
    // Add user message to chat history
    const newMessage = {
      isBot: false, 
      content: messageContent,
      image: capturedImage
    };
    
    setMessages(prev => [...prev, newMessage]);
    setInput("");
    setTranscript("");
    setIsProcessing(true);
    
    try {
      // Stop any currently playing audio
      if (currentAudio) {
        currentAudio.pause();
      }
      
      // Call backend API with TTS flag based on user preference
      const response = await getAyaResponse(
        messageContent,
        formatMessagesForApi(),
        base64Image, // Send base64 encoded image
        audioEnabled // Send the audio preference
      );
      
      // Add the response to chat
      setMessages(prev => [
        ...prev,
        {
          isBot: true,
          content: response.response,
          messageId: response.message_id,
          audioUrl: response.audio_url // Store audio URL with message
        }
      ]);
      
      // Play audio if enabled and URL is available
      if (audioEnabled && response.audio_url) {
        const audio = new Audio(response.audio_url);
        setCurrentAudio(audio);
        
        audio.onended = () => {
          setCurrentAudio(null);
        };
        
        audio.onerror = (e) => {
          console.error("Audio playback error:", e);
          setCurrentAudio(null);
        };
        
        audio.play().catch(error => {
          console.error('Error playing audio:', error);
        });
      }
    } catch (error) {
      console.error("Error getting response:", error);
      // Show error message to user
      setMessages(prev => [
        ...prev,
        {
          isBot: true,
          content: "Sorry, I encountered an error processing your request. Please try again later.",
          error: true
        }
      ]);
    } finally {
      setIsProcessing(false);
      setCapturedImage(null);
    }
  };

  const startRecording = () => {
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      setTranscript("");
      audioChunksRef.current = []; // Reset audio chunks
      
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
          
          // Start timer
          timerIntervalRef.current = setInterval(() => {
            setTimer(prev => prev + 1);
          }, 1000);
          
          // Setup audio analysis
          const AudioContext = window.AudioContext || window.webkitAudioContext;
          const audioCtx = new AudioContext();
          const analyser = audioCtx.createAnalyser();
          analyser.fftSize = 2048;
          
          const source = audioCtx.createMediaStreamSource(stream);
          source.connect(analyser);
          
          // Setup MediaRecorder to collect audio chunks
          const mediaRecorder = new MediaRecorder(stream);
          mediaRecorderRef.current = {
            stream,
            analyser,
            audioContext: audioCtx,
            mediaRecorder,
          };
          
          // Listen for data available event
          mediaRecorder.ondataavailable = (event) => {
            if (event.data.size > 0) {
              audioChunksRef.current.push(event.data);
            }
          };
          
          // Start recording
          mediaRecorder.start(100); // Collect data every 100ms
        })
        .catch((error) => {
          alert("Microphone access error: " + error.message);
          console.log(error);
        });
    } else {
      alert("Your browser doesn't support microphone access.");
    }
  };

  const stopRecording = async () => {
    setIsProcessing(true);
    
    // Stopping the speech recognition
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    }
    
    // Stop timer
    clearInterval(timerIntervalRef.current);
    setTimer(0);
    
    // Get all media recorder details
    const { stream, analyser, audioContext, mediaRecorder } = mediaRecorderRef.current;
    
    // Create a promise to ensure we get the final chunk of audio
    const finalAudioChunk = new Promise((resolve) => {
      mediaRecorder.onstop = () => {
        resolve();
      };
    });
    
    // Stop the media recorder
    if (mediaRecorder && mediaRecorder.state !== 'inactive') {
      mediaRecorder.stop();
    }
    
    // Wait for final audio chunk
    await finalAudioChunk;
    
    // Clean up resources
    if (analyser) {
      analyser.disconnect();
    }
    
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
    }
    
    if (audioContext && audioContext.state !== 'closed') {
      audioContext.close();
    }
    
    setIsRecording(false);
    
    // Clean up animation
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
    
    // If we have transcript from Web Speech API, use it
    if (transcript.trim()) {
      setInput(transcript);
      await handleSendMessage();
    } 
    // Otherwise, if we have audio chunks, send them to our backend for transcription
    else if (audioChunksRef.current.length > 0) {
      try {
        // Combine all audio chunks into a single blob
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        
        // Convert blob to arrayBuffer
        const arrayBuffer = await audioBlob.arrayBuffer();
        
        // Call our backend service to get transcription using the current model
        const result = await streamAudioForTranscription(arrayBuffer, currentModel);
        
        if (result && result.trim()) {
          // Use the transcription as input
          setInput(result);
          // Send as a message
          await handleSendMessage();
        } else {
          setIsProcessing(false);
          alert("Sorry, I couldn't understand what you said. Please try again.");
        }
      } catch (error) {
        console.error("Error processing audio:", error);
        setIsProcessing(false);
        alert("There was an error processing your audio. Please try again.");
      }
    } else {
      setIsProcessing(false);
    }
  };

  // Function to toggle text-to-speech
  const toggleAudio = () => {
    // If turning off, stop any currently playing audio
    if (audioEnabled && currentAudio) {
      currentAudio.pause();
      setCurrentAudio(null);
    }
    setAudioEnabled(!audioEnabled);
  };

  // Function to replay the most recent bot message audio
  const replayLastAudio = () => {
    // Find the most recent bot message with audio
    const lastBotMessageWithAudio = [...messages].reverse().find(msg => msg.isBot && msg.audioUrl);
    
    if (lastBotMessageWithAudio && lastBotMessageWithAudio.audioUrl) {
      // Stop any currently playing audio
      if (currentAudio) {
        currentAudio.pause();
      }
      
      // Play the audio
      const audio = new Audio(lastBotMessageWithAudio.audioUrl);
      setCurrentAudio(audio);
      
      audio.onended = () => {
        setCurrentAudio(null);
      };
      
      audio.play().catch(error => {
        console.error('Error playing audio:', error);
      });
    }
  };

  // Audio visualization
  useEffect(() => {
    if (!canvasRef.current || !isRecording) return;

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
      const analyser = mediaRecorderRef.current.analyser;
      if (!analyser) return;
      
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

    visualizeVolume();

    return () => {
      cancelAnimationFrame(animationRef.current || 0);
    };
  }, [isRecording]);

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  return (
    <div className="flex flex-col h-screen bg-white text-gray-800 font-sans">
      {/* Chat messages area - improved with fixed height and overflow handling */}
      <div 
        ref={messageContainerRef}
        className="flex-1 px-4 pb-36 pt-4 max-w-5xl mx-auto w-full"
      >
        <div className="flex flex-col gap-6">
          {messages.map((message, index) => (
            <div key={index} className={`flex ${message.isBot ? "" : "justify-end"}`}>
              <div 
                className={`max-w-3xl px-4 py-3 ${
                  message.isBot 
                    ? "border-b border-gray-200 pb-6" 
                    : "bg-orange-400 text-white rounded-2xl"
                }`}
              >
                {message.image && (
                  <div className="mb-3">
                    <img 
                      src={message.image} 
                      alt="Uploaded" 
                      className="max-w-xs rounded-lg shadow-sm" 
                    />
                  </div>
                )}
                <p className="whitespace-pre-wrap">{message.content}</p>
                
                {/* Audio controls for bot messages with audio URLs */}
                {message.isBot && message.audioUrl && (
                  <div className="mt-2 text-right">
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      className="text-gray-500 hover:text-gray-700"
                      onClick={() => playResponseAudio(message.audioUrl)}
                    >
                      <Volume2 className="h-4 w-4 mr-1" />
                      <span className="text-xs">Listen</span>
                    </Button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
        <div ref={messagesEndRef} />
      </div>

      {/* Camera overlay */}
      {showCamera && (
        <CameraCapture
          onCapture={(imageData) => {
            setCapturedImage(imageData);
            setShowCamera(false);
          }}
          onClose={() => setShowCamera(false)}
        />
      )}

      {/* Preview captured image */}
      {capturedImage && (
        <div className="fixed bottom-24 left-0 right-0 flex justify-center z-10">
          <div className="bg-white p-2 rounded-lg shadow-lg">
            <img src={capturedImage} alt="Captured" className="h-24 rounded" />
            <button 
              onClick={() => setCapturedImage(null)} 
              className="absolute top-1 right-1 bg-gray-800 text-white rounded-full p-1 text-xs"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Settings Drawer */}
      <Drawer open={drawerOpen} onOpenChange={setDrawerOpen}>
        <DrawerContent>
          <div className="mx-auto w-full max-w-sm">
            <DrawerHeader>
              <DrawerTitle>Settings</DrawerTitle>
              <DrawerDescription>
                Configure transcription and audio settings
              </DrawerDescription>
            </DrawerHeader>
            
            <div className="p-4 pb-0">
              <div className="mb-6">
                <h4 className="font-medium mb-2 text-sm">Transcription Model</h4>
                <div className="flex flex-wrap gap-2">
                  {loadingModels ? (
                    <div className="flex items-center">
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      <span>Loading models...</span>
                    </div>
                  ) : (
                    availableModels.map(model => (
                      <Button
                        key={model}
                        variant={model === currentModel ? "default" : "outline"}
                        size="sm"
                        onClick={() => handleModelChange(model)}
                        disabled={loadingModels}
                      >
                        {model}
                      </Button>
                    ))
                  )}
                </div>
                <p className="text-xs text-gray-500 mt-2">
                  Current model: <span className="font-medium">{currentModel}</span>
                </p>
              </div>
              
              <div className="mb-6">
                <h4 className="font-medium mb-2 text-sm">Text-to-Speech</h4>
                <Button
                  variant={audioEnabled ? "default" : "outline"}
                  size="sm"
                  onClick={toggleAudio}
                >
                  {audioEnabled ? (
                    <><Volume2 className="h-4 w-4 mr-1" /> Enabled</>
                  ) : (
                    <><VolumeX className="h-4 w-4 mr-1" /> Disabled</>
                  )}
                </Button>
              </div>
            </div>
            
            <DrawerFooter>
              <DrawerClose asChild>
                <Button variant="outline">Close</Button>
              </DrawerClose>
            </DrawerFooter>
          </div>
        </DrawerContent>
      </Drawer>

      {/* Input area - fixed at the bottom */}
      <div className="fixed bottom-0 left-0 right-0 p-4 border-t bg-white shadow-lg">
        {/* Audio toggle and Settings buttons */}
        <div className="flex justify-between max-w-3xl mx-auto mb-2 px-2">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            className="text-sm flex items-center gap-1 text-gray-500"
            onClick={() => setDrawerOpen(true)}
          >
            <Settings className="h-4 w-4" />
            <span>Settings</span>
          </Button>

          <Button
            type="button"
            variant="ghost"
            size="sm"
            className={`text-sm flex items-center gap-1 ${audioEnabled ? 'text-blue-500' : 'text-gray-500'}`}
            onClick={toggleAudio}
          >
            {audioEnabled ? (
              <>
                <Volume2 className="h-4 w-4" />
                <span>TTS Enabled</span>
              </>
            ) : (
              <>
                <VolumeX className="h-4 w-4" />
                <span>TTS Disabled</span>
              </>
            )}
          </Button>
        </div>
        
        <form onSubmit={handleSendMessage} className="relative max-w-3xl mx-auto">
          <div className="flex items-center">
            <div className="absolute left-3 flex gap-2 z-10">
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="text-gray-500 hover:text-gray-700"
                onClick={() => setShowCamera(true)}
                disabled={isRecording || isProcessing}
              >
                <span className="sr-only">Take photo</span>
                <Camera className="h-5 w-5" />
              </Button>
            </div>
            
            {isRecording ? (
              <div className="w-full relative m-auto">
                {/* Audio Recording UI */}
                <div className="w-8/10 m-auto h-12 bg-white border rounded-full overflow-hidden px-4 py-2 flex items-center gap-2">
                  {/* Recording indicator */}
                  <div className="h-2 w-2 rounded-full bg-red-500 animate-pulse" />
                  
                  {/* Timer */}
                  <div className="text-xs font-mono text-gray-500">
                    {`${hourLeft}${hourRight}:${minuteLeft}${minuteRight}:${secondLeft}${secondRight}`}
                  </div>
                  
                  {/* Visualizer */}
                  <div className="flex-1 h-full relative">
                    <canvas 
                      ref={canvasRef} 
                      className="w-full h-full" 
                      width="300" 
                      height="48"
                    />
                  </div>
                  
                  {/* Live transcript */}
                  {transcript && (
                    <div className="max-w-sm truncate text-sm ml-2">
                      {transcript}
                    </div>
                  )}
                  
                  {/* Stop button */}
                  <Button
                    type="button"
                    variant="ghost"
                    size="icon"
                    className="text-gray-500 hover:text-gray-700"
                    onClick={stopRecording}
                    disabled={isProcessing}
                  >
                    <span className="sr-only">Stop recording</span>
                    <Square className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ) : (
              <Input
                type="text"
                placeholder={isProcessing ? "Processing..." : "Ask Aya Vision"}
                className="w-full pr-24 pl-12 py-6 border rounded-full bg-white"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={isProcessing}
              />
            )}
            
            <div className="absolute right-3 top-1/2 transform -translate-y-1/2 flex gap-2">
              {!isRecording && !isProcessing && (
                <Button
                  type="button"
                  variant="ghost"
                  size="icon"
                  className="text-gray-500 hover:text-gray-700"
                  onClick={startRecording}
                  disabled={isProcessing}
                >
                  <span className="sr-only">Use microphone</span>
                  <Mic className="h-5 w-5" />
                </Button>
              )}
              <Button
                type="submit"
                variant="ghost"
                size="icon"
                className="text-gray-500 hover:text-gray-700"
                disabled={isProcessing || (input.trim() === "" && !capturedImage)}
              >
                <span className="sr-only">Send</span>
                {isProcessing ? (
                  <Loader2 className="h-5 w-5 animate-spin" />
                ) : (
                  <Send className="h-5 w-5" />
                )}
              </Button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}