'use client';

import React, { useState, useEffect } from 'react';

export default function AnimatedWaveform({ isAISpeaking = false, isUserSpeaking = false }) {
  // Number of bars in the waveform
  const numBars = 7;
  
  // Create an array of random heights for the initial state
  const [barHeights, setBarHeights] = useState(
    Array.from({ length: numBars }, () => Math.random() * 0.5 + 0.2)
  );
  
  useEffect(() => {
    let animationFrame;
    let intervalId;
    
    const animateBars = () => {
      if (isAISpeaking || isUserSpeaking) {
        // Update bar heights more frequently when speaking
        intervalId = setInterval(() => {
          setBarHeights(prevHeights => 
            prevHeights.map(() => {
              // Create more dramatic movement when speaking
              const minHeight = isUserSpeaking ? 0.3 : 0.2;
              const variance = isUserSpeaking ? 0.7 : 0.5;
              return Math.random() * variance + minHeight;
            })
          );
        }, 150); // Update every 150ms
      } else {
        // Subtle movement when not speaking
        intervalId = setInterval(() => {
          setBarHeights(prevHeights => 
            prevHeights.map(height => {
              // Small random adjustments to current height
              const change = (Math.random() - 0.5) * 0.1;
              return Math.max(0.1, Math.min(0.4, height + change));
            })
          );
        }, 800); // Slower updates when idle
      }
    };
    
    animateBars();
    
    return () => {
      cancelAnimationFrame(animationFrame);
      clearInterval(intervalId);
    };
  }, [isAISpeaking, isUserSpeaking]);
  
  return (
    <div className="flex items-center justify-center h-full w-full">
      <div className={`flex items-center justify-center space-x-1 ${isUserSpeaking ? 'scale-110 transition-transform' : 'transition-transform'}`}>
        {barHeights.map((height, index) => {
          // Center bar is tallest
          const centerMultiplier = Math.abs(index - Math.floor(numBars/2)) < 2 ? 1.5 : 1;
          const barHeight = height * centerMultiplier;
          const maxHeight = 100; // Maximum height in pixels
          
          return (
            <div
              key={index}
              className="w-4 bg-black rounded-full transition-all duration-150 ease-in-out"
              style={{
                height: `${barHeight * maxHeight}px`,
                opacity: isAISpeaking ? 1 : 0.85,
              }}
            />
          );
        })}
      </div>
    </div>
  );
};