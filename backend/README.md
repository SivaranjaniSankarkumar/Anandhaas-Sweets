# Anandhaas Backend API

Flask backend that integrates with the React dashboard frontend.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Copy your `anandhaas_data.csv` file to this directory

3. Configure environment variables in `.env`:
   - SARVAM_API_KEY: Your Sarvam AI API key
   - AWS credentials for Bedrock access

4. Run the server:
```bash
python app.py
```

Server runs on http://localhost:5000

## API Endpoints

- `GET /api/dashboard-data` - Get dashboard metrics
- `POST /api/query` - Process voice/text queries
- `POST /api/transcribe` - Audio transcription
- `POST /api/tts` - Text-to-speech

## Frontend Integration

The React frontend connects to these endpoints for:
- Real-time dashboard data
- Voice assistant functionality
- Chart generation from queries