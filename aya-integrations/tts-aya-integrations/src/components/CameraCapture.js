"use client";
import { useEffect, useRef, useState } from "react";

const CameraCapture = ({ onCapture, onClose }) => {
  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const [stream, setStream] = useState(null);

  useEffect(() => {
    const startCamera = async () => {
      try {
        const mediaStream = await navigator.mediaDevices.getUserMedia({ video: true });
        setStream(mediaStream);
        if (videoRef.current) {
          videoRef.current.srcObject = mediaStream;
        }
      } catch (err) {
        console.error("Camera access failed:", err);
      }
    };

    startCamera();

    return () => {
      if (stream) {
        stream.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  const handleTakePicture = () => {
    const canvas = canvasRef.current;
    const video = videoRef.current;

    if (canvas && video) {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;

      const ctx = canvas.getContext("2d");
      ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
      const imageData = canvas.toDataURL("image/png");

      if (onCapture) onCapture(imageData);
      if (stream) stream.getTracks().forEach((track) => track.stop());
      if (onClose) onClose();
    }
  };

  return (
    <div className="absolute bottom-24 right-6 bg-white shadow-xl rounded-xl p-4 z-50 w-[300px]">
      <video ref={videoRef} autoPlay playsInline className="rounded shadow-lg max-w-md w-full" />
      <canvas ref={canvasRef} style={{ display: "none" }} />
      <div className="mt-3 flex justify-center space-x-3">
        <button onClick={handleTakePicture} className="bg-black text-white px-3 py-1 rounded">Capture</button>
        <button onClick={onClose} className="bg-black text-white px-3 py-1 rounded">Cancel</button>
      </div>
    </div>
  );
};

export default CameraCapture;
