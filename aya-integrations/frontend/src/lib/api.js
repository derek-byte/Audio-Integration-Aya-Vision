// api.js - Enhanced service for API calls to our backend with TTS support

/**
 * Send transcription to backend and get Aya Vision response with speech synthesis
 * @param {string} message - The transcribed message
 * @param {Array} chatHistory - Previous chat messages for context
 * @param {string|null} imageData - Optional base64 image data
 * @param {boolean} withSpeech - Whether to request speech synthesis
 * @returns {Promise<Object>} - Response from Aya Vision API with optional audio URL
 */
export const getAyaResponse = async (message, chatHistory = [], imageData = null, withSpeech = false) => {
    try {
      // Determine which endpoint to use based on speech synthesis requirement
      const endpoint = withSpeech ? 'aya-response-tts' : 'aya-response';
      
      const response = await fetch(`http://localhost:5000/${endpoint}`, {
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
  
      const result = await response.json();
      
      // If speech was requested, play the audio
      if (withSpeech && result.audio_url) {
        playResponseAudio(result.audio_url);
      }
      
      return result;
    } catch (error) {
      console.error('Error getting Aya response:', error);
      throw error;
    }
  };
  
  /**
   * Get text-to-speech for a specific text
   * @param {string} text - Text to synthesize
   * @returns {Promise<string>} - URL to audio file
   */
  export const getSpeechFromText = async (text) => {
    try {
      const response = await fetch('http://localhost:5000/synthesize', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          text,
        }),
      });
  
      if (!response.ok) {
        throw new Error(`Error: ${response.status}`);
      }
  
      const blob = await response.blob();
      return URL.createObjectURL(blob);
    } catch (error) {
      console.error('Error synthesizing speech:', error);
      throw error;
    }
  };
  
  /**
   * Play audio response from URL
   * @param {string} audioUrl - URL to audio file
   */
  export const playResponseAudio = (audioUrl) => {
    const audio = new Audio(audioUrl);
    audio.play().catch(error => {
      console.error('Error playing audio:', error);
    });
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