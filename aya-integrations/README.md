# NextJS to Flask STT Integration Setup

## Project Structure
```
project/
├── frontend/             # NextJS Frontend
│   ├── pages/
│   │   └── speech-to-text.js
│   ├── package.json
│   └── ...
│
└── backend/              # Flask Backend
    ├── app.py
    ├── requirements.txt
    └── ...
```

## Setup Instructions

### 1. Install Required Packages

#### Frontend (NextJS)
```bash
cd frontend
npm install next react react-dom
```

#### Backend (Flask)
```bash
cd backend
pip install flask flask-cors flask-sock gunicorn

# Install your STT model library
# For example, if using OpenAI's Whisper:
# pip install openai-whisper
```

### 2. Create requirements.txt for Backend
```
flask==2.3.3
flask-cors==4.0.0
flask-sock==0.6.0
gunicorn==21.2.0
# Add your STT model requirements here
# For example:
# openai-whisper==20230314
```

### 3. Configure CORS for Production

For production, update the CORS configuration in your Flask app:

```python
# Update in app.py
CORS(app, resources={r"/*": {"origins": "https://your-nextjs-domain.com"}})
```

## Running the Application

### Development Environment

#### Start the Flask Backend
```bash
cd backend
python app.py
```

#### Start the NextJS Frontend
```bash
cd frontend
npm run dev
```

### Production Deployment

#### Flask Backend (Using Gunicorn)
```bash
cd backend
gunicorn -k geventwebsocket.gunicorn.workers.GeventWebSocketWorker -w 1 app:app
```

#### NextJS Frontend
```bash
cd frontend
npm run build
npm start
```

## Implementation Notes

### 1. Integration with Your STT Model

Replace the placeholder `process_audio` and `process_audio_file` functions in the Flask backend with your actual STT model implementation. For example:

```python
# If using Whisper
import whisper

# Load model once at startup
model = whisper.load_model("base")  # Choose model size based on your needs

def process_audio(audio_bytes):
    # Create a temporary file from bytes
    with tempfile.NamedTemporaryFile(suffix='.webm', delete=True) as temp_file:
        temp_file.write(audio_bytes)
        temp_file.flush()
        
        # Process with Whisper
        result = model.transcribe(temp_file.name)
        return result["text"]
```

### 2. WebSocket Connection URL

Update the WebSocket URL in the NextJS component based on your environment:

```javascript
// Development
const wsUrl = 'ws://localhost:5000/stream-audio';

// Production
// const wsUrl = 'wss://your-backend-domain.com/stream-audio';

socketRef.current = new WebSocket(wsUrl);
```

### 3. Error Handling and Reconnection Logic

For production, enhance the WebSocket connection with reconnection logic:

```javascript
function setupWebSocket() {
  socketRef.current = new WebSocket(wsUrl);
  
  // Set up event handlers...
  
  socketRef.current.onclose = (event) => {
    console.log('WebSocket closed, attempting to reconnect...');
    setTimeout(setupWebSocket, 3000);  // Reconnect after 3 seconds
  };
}
```

### 4. Security Considerations

- Limit audio file size
- Implement user authentication
- Use HTTPS/WSS in production
- Consider rate limiting on the backend

## Customizing the UI

The current UI is minimalist. You can enhance it with:

- A visual audio level meter
- Real-time visual feedback when audio is detected
- Additional controls for language selection if your STT model supports it
- A history of past transcriptions