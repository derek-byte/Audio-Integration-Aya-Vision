// api.js - Service for API calls to our backend

/**
 * Send transcription to backend and get Aya Vision response
 * @param {string} message - The transcribed message
 * @param {Array} chatHistory - Previous chat messages for context
 * @param {string|null} imageData - Optional base64 image data
 * @returns {Promise<Object>} - Response from Aya Vision API
 */
export const getAyaResponse = async (message, chatHistory = [], imageData = null) => {
    try {
      const response = await fetch('http://localhost:5000/aya-response', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message,
          chatHistory,
          image: imageData,
        }),
      });
  
      if (!response.ok) {
        throw new Error(`Error: ${response.status}`);
      }
  
      return await response.json();
    } catch (error) {
      console.error('Error getting Aya response:', error);
      throw error;
    }
  };
  
  /**
   * Send audio data to backend for streaming transcription
   * @param {ArrayBuffer} audioData - Raw audio data
   * @returns {Promise<string>} - Transcription
   */
  export const streamAudioForTranscription = (audioData) => {
    return new Promise((resolve, reject) => {
      const socket = new WebSocket('ws://localhost:5000/stream-audio');
      
      socket.onopen = () => {
        console.log('WebSocket connection established');
        // Convert ArrayBuffer to Base64
        const base64Audio = btoa(
          new Uint8Array(audioData).reduce((data, byte) => data + String.fromCharCode(byte), '')
        );
        socket.send(JSON.stringify({ audio_data: base64Audio }));
      };
      
      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.transcription) {
            resolve(data.transcription);
            socket.close();
          }
        } catch (e) {
          console.error('Error parsing WebSocket message:', e);
        }
      };
      
      socket.onerror = (error) => {
        console.error('WebSocket error:', error);
        reject(error);
      };
      
      socket.onclose = () => {
        console.log('WebSocket connection closed');
      };
    });
  };