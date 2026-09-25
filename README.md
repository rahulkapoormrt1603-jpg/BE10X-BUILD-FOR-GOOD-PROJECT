# UNStammer Speech Assessment Backend

Production-ready Flask backend for speech analysis using Whisper + librosa. Deployed on Render.

## Features

- **Speech Transcription**: OpenAI Whisper model for accurate speech-to-text
- **Pause Detection**: Identifies silences >0.5 seconds using energy-based detection
- **Stutter Pattern Recognition**: Detects word/syllable repetitions and stuttering patterns
- **Speech Rate Analysis**: Calculates WPM and variance scoring (>150 or <80 WPM)
- **Filler Word Detection**: Identifies common fillers (um, uh, aar, haan, etc.)
- **Severity Scoring**: Normalized 0-100 score with 3-tier categorization
- **PDF Guides**: Serves personalized recovery guides based on severity
- **CORS Enabled**: Ready for frontend integration
- **Error Handling**: Comprehensive validation and error responses

## Scoring System

```
Component Scores:
- Pause Score: pause_count × 5
- Repetition Score: repetition_count × 3
- Variance Score: 15 (if WPM > 150 or < 80) or 10 (otherwise)
- Filler Score: filler_count × 1

Final Score = min((total_raw / 200) × 100, 100)

Severity Categories:
- 0-40: Minimal
- 40-70: Mild
- 70+: Severe
```

## Installation

### Local Development

```bash
# Clone repository
git clone <repo-url>
cd unstammer-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
echo "FLASK_ENV=development
WHISPER_MODEL=base
PDF_FOLDER=pdfs" > .env

# Create pdfs folder
mkdir pdfs

# Add PDF guides (minimal_guide.pdf, mild_guide.pdf, severe_guide.pdf) to pdfs/ folder

# Run locally
python app.py
```

Visit: `http://localhost:5000/health`

### Render Deployment

#### 1. Create Render Service

- Go to [render.com](https://render.com)
- Click "New +" → "Web Service"
- Connect GitHub repository
- Configure:
  - **Name**: unstammer-backend
  - **Environment**: Python 3.9
  - **Build Command**: `pip install -r requirements.txt`
  - **Start Command**: `gunicorn app:app`

#### 2. Set Environment Variables

In Render dashboard, add:
```
FLASK_ENV=production
WHISPER_MODEL=base
PDF_FOLDER=/var/www/pdfs
PORT=5000
```

#### 3. Add PDF Files

Before deployment, create a `pdfs/` folder in repo root with:
- `minimal_guide.pdf`
- `mild_guide.pdf`
- `severe_guide.pdf`

Or upload after deployment to Render's persistent disk.

#### 4. Deploy

Push to GitHub → Render auto-deploys.

Your API is live at: `https://your-service-name.onrender.com`

## API Endpoints

### Health Check
```bash
GET /health
```
Response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:45.123456"
}
```

### Analyze Speech (Main Endpoint)
```bash
POST /analyze
Content-Type: multipart/form-data

Body:
  file: <video/audio file>
```

**Supported Formats**: mp4, mov, avi, wav, mp3, webm, flac (max 100MB)

**Response (200 OK)**:
```json
{
  "severity_score": 52.5,
  "category": "mild",
  "metrics": {
    "pause_count": 3,
    "repetition_count": 2,
    "speech_rate": 125.5,
    "filler_count": 4,
    "audio_duration_seconds": 45.2,
    "transcribed_text": "The quick brown fox..."
  },
  "component_scores": {
    "pause_score": 15,
    "repetition_score": 6,
    "variance_score": 10,
    "filler_score": 4
  },
  "pdf_type": "mild",
  "file_url": "/download-guide/mild",
  "timestamp": "2024-01-15T10:30:45.123456"
}
```

**Error Response (400/500)**:
```json
{
  "error": "Error message describing what went wrong"
}
```

### Download PDF Guide
```bash
GET /download-guide/<type>
```

**Types**: `minimal`, `mild`, `severe`

**Response**: PDF file download

## Error Handling

| Status | Error | Solution |
|--------|-------|----------|
| 400 | No file provided | Include file in `multipart/form-data` |
| 400 | File format not supported | Use mp4, mov, avi, wav, mp3, webm, or flac |
| 413 | File too large | Max 100MB; split audio if needed |
| 400 | No speech detected | Ensure clear audio in file |
| 404 | PDF not found | Verify PDF exists in `pdfs/` folder |
| 500 | Server error | Check logs; verify Whisper model loaded |

## Frontend Integration

### Example: React/Next.js

```typescript
const analyzeUtterance = async (videoFile: File) => {
  const formData = new FormData();
  formData.append('file', videoFile);

  const response = await fetch(
    'https://your-service.onrender.com/analyze',
    { method: 'POST', body: formData }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.error);
  }

  return await response.json();
};
```

## Configuration

### Environment Variables

- **FLASK_ENV**: `development` or `production`
- **WHISPER_MODEL**: `tiny`, `base`, `small`, `medium`, `large` (default: `base`)
  - tiny: ~39M (fastest)
  - base: ~140M (recommended)
  - small: ~244M
  - large: ~3GB (most accurate)
- **PDF_FOLDER**: Path to folder containing PDF guides (default: `pdfs`)
- **PORT**: Server port (default: 5000, overridden by Render)

### Tuning Performance

**Faster Processing** (trade accuracy):
```
WHISPER_MODEL=tiny
```

**Better Accuracy** (slower):
```
WHISPER_MODEL=small  # or medium/large
```

**Memory Optimization** for Render:
- Use `base` model (fits in standard dyno)
- Add `/tmp` cleanup in production
- Monitor Render dashboard for memory usage

## Monitoring

### Render Dashboard
- View logs: Logs tab
- Monitor: Metrics tab (CPU, Memory, Build status)
- Alerts: Add email notifications for crashes

### Local Logging
Add to `app.py`:
```python
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

### Example Log Output
```
2024-01-15 10:30:45 - INFO - File received: video.mp4
2024-01-15 10:30:47 - INFO - Transcription complete: 320 words
2024-01-15 10:30:48 - INFO - Analysis complete: score=52.5
```

## Testing

### Unit Tests (pytest)

```bash
pip install pytest requests-mock

# Run tests
pytest tests/
```

### Manual Testing

```bash
# Health check
curl https://your-service.onrender.com/health

# Upload and analyze
curl -F "file=@sample_audio.mp3" \
  https://your-service.onrender.com/analyze

# Download guide
curl -o guide.pdf \
  https://your-service.onrender.com/download-guide/mild
```

## Troubleshooting

### "Whisper model not loaded"
- Check model specified in `WHISPER_MODEL` env var
- Render needs ~1-2GB disk for model download
- First request takes longer (model caching)

### "No speech detected"
- Audio quality too low (try clearer recording)
- Language not English (Whisper defaults to auto-detect)
- Silence too long before speech starts

### "PDF not found"
- Verify PDFs in `pdfs/` folder on Render
- After deployment, upload via Render Dashboard or Git

### Timeout on Large Files
- Max file size: 100MB
- Whisper processing takes ~10-30s per minute of audio
- Consider chunking audio for very long recordings

## Architecture

```
Request → File Validation
        → Audio Extraction (librosa)
        → Transcription (Whisper)
        → Pause Detection (energy analysis)
        → Pattern Recognition (repetitions/fillers)
        → Scoring Algorithm
        → Response + PDF Mapping
```

## Performance

| Metric | Value |
|--------|-------|
| Typical Response Time | 10-30s (depending on audio length) |
| Memory Usage | ~500MB-1GB (base model) |
| Supported Concurrency | 1-3 requests (standard Render dyno) |
| Max File Size | 100MB |

For production with >5 concurrent users, upgrade Render dyno.

## Security Notes

- File uploads validated by extension + MIME type
- Max 100MB enforced via Flask config
- Temp files auto-deleted after processing
- PDF folder should contain only intended guides
- Consider rate limiting for production

## License

MIT License - See LICENSE file

## Support

For issues:
1. Check logs: Render Dashboard → Logs
2. Verify PDFs exist: `ls -la pdfs/`
3. Test health: `curl /health`
4. Review this README's Troubleshooting section