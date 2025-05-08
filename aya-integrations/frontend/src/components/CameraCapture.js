"use client";
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { X, Camera } from "lucide-react";

const CameraCapture = ({ onCapture, onClose }) => {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [stream, setStream] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const startCamera = async () => {
      setIsLoading(true);
      try {
        const mediaStream = await navigator.mediaDevices.getUserMedia({ 
          video: { facingMode: "environment" } 
        });
        setStream(mediaStream);
        if (videoRef.current) {
          videoRef.current.srcObject = mediaStream;
        }
      } catch (err) {
        console.error("Camera access failed:", err);
        alert("Failed to access camera. Please check your camera permissions.");
        onClose();
      } finally {
        setIsLoading(false);
      }
    };

    startCamera();

    return () => {
      stopCameraStream();
    };
  }, []);

  const stopCameraStream = () => {
    if (stream) {
      stream.getTracks().forEach((track) => track.stop());
    }
  };

  const handleTakePicture = () => {
    const canvas = canvasRef.current;
    const video = videoRef.current;

    if (canvas && video) {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;

      const ctx = canvas.getContext("2d");
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      const imageData = canvas.toDataURL("image/png");

      stopCameraStream();
      if (onCapture) onCapture(imageData);
      if (onClose) onClose();
    }
  };

  const handleClose = () => {
    stopCameraStream();
    if (onClose) onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center backdrop-blur-[2px] backdrop-brightness-40">
      <div className="relative bg-white rounded-lg shadow-xl overflow-hidden max-w-md w-full mx-4">
        {/* Header */}
        <div className="flex justify-between items-center p-4 border-b">
          <h3 className="font-medium">Take a photo</h3>
          <Button 
            variant="ghost" 
            size="icon" 
            onClick={handleClose} 
            className="h-8 w-8 rounded-full"
          >
            <X size={18} />
          </Button>
        </div>
        
        {/* Camera view */}
        <div className="relative bg-black w-full aspect-video flex items-center justify-center">
          {isLoading && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-8 h-8 border-4 border-t-blue-500 border-r-transparent border-b-transparent border-l-transparent rounded-full animate-spin"></div>
            </div>
          )}
          <video 
            ref={videoRef} 
            autoPlay 
            playsInline 
            className="max-h-full max-w-full object-contain"
            onCanPlay={() => setIsLoading(false)} 
          />
          <canvas ref={canvasRef} style={{ display: "none" }} />
        </div>
        
        {/* Controls */}
        <div className="p-4 flex justify-center">
          <Button 
            onClick={handleTakePicture}
            disabled={isLoading}
            className="w-16 h-16 rounded-full bg-white border-2 border-gray-300 hover:bg-gray-100 flex items-center justify-center"
          >
            <div className="w-12 h-12 rounded-full flex items-center justify-center">
              <Camera size={24} className="text-stone-400" />
            </div>
          </Button>
        </div>
      </div>
    </div>
  );
};

export default CameraCapture;