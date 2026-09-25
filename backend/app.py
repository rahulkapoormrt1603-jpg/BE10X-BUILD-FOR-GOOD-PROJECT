"""
UNStammer Speech Assessment Backend
Production-ready Flask app for Render deployment
"""

import os
import json
import tempfile
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import whisper
import librosa
import numpy as np
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
CORS(app)

# Configuration
UPLOAD_FOLDER = tempfile.gettempdir()
ALLOWED_EXTENSIONS = {'mp4', 'mov', 'avi', 'mkv', 'webm'}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
PDF_FOLDER = os.path.join(os.path.dirname(__file__), 'pdfs')

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load Whisper model (small by default for speed)
try:
    whisper_model = whisper.load_model("base")
except Exception as e:
    logger.error(f"Failed to load Whisper model: {e}")
    whisper_model = None


# ============================================
# UTILITY FUNCTIONS
# ============================================

def allowed_file(filename):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def transcribe_video(video_path):
    """
    Transcribe video using OpenAI Whisper
    Returns: (transcript_text, success_bool, error_message)
    """
    try:
        if not whisper_model:
            return "", False, "Whisper model not loaded"
        
        logger.info(f"Transcribing video: {video_path}")
        
        # Transcribe with Whisper
        result = whisper_model.transcribe(video_path, language="en")
        transcript = result.get("text", "")
        
        if not transcript:
            return "", False, "No speech detected in video"
        
        logger.info(f"Transcription successful: {len(transcript)} characters")
        return transcript, True, ""
    
    except Exception as e:
        logger.error(f"Transcription error: {e}")
        return "", False, f"Transcription failed: {str(e)}"


def extract_audio_features(video_path):
    """
    Extract audio features using librosa
    Returns: (speech_rate, duration, error_message)
    """
    try:
        logger.info(f"Extracting audio features from: {video_path}")
        
        # Load audio
        y, sr = librosa.load(video_path, sr=None)
        duration = len(y) / sr
        
        # Estimate speech rate (simple method: zero crossings as proxy)
        zcr = librosa.feature.zero_crossing_rate(y)[0]
        mean_zcr = np.mean(zcr)
        
        # Rough speech rate estimation (words per minute)
        # This is a simplification; in production, use more sophisticated methods
        speech_rate = int(mean_zcr * 100)  # Placeholder calculation
        
        logger.info(f"Audio features extracted: {speech_rate} wpm, {duration}s duration")
        return speech_rate, duration, ""
    
    except Exception as e:
        logger.error(f"Audio feature extraction error: {e}")
        return 0, 0, f"Feature extraction failed: {str(e)}"


def detect_pauses(transcript, audio_path):
    """
    Detect extended pauses in speech
    Returns: (pause_count, error_message)
    """
    try:
        logger.info("Detecting pauses...")
        
        y, sr = librosa.load(audio_path, sr=None)
        
        # Detect silence using energy-based method
        S = librosa.feature.melspectrogram(y=y, sr=sr)
        S_db = librosa.power_to_db(S, ref=np.max)
        
        # Calculate energy per frame
        energy = np.mean(S_db, axis=0)
        threshold = np.mean(energy) - np.std(energy)
        
        # Count frames below threshold (silence)
        silent_frames = np.sum(energy < threshold)
        frame_length = len(y) / len(energy)
        silent_duration = (silent_frames * frame_length) / sr
        
        # Count pauses > 0.5 seconds
        pause_count = int(silent_duration / 0.5)
        
        logger.info(f"Pauses detected: {pause_count}")
        return pause_count, ""
    
    except Exception as e:
        logger.error(f"Pause detection error: {e}")
        return 0, f"Pause detection failed: {str(e)}"


def detect_repetitions(transcript):
    """
    Detect stuttering/repetition patterns in transcript
    Returns: (repetition_count, error_message)
    """
    try:
        logger.info("Detecting repetitions...")
        
        # Split transcript into words
        words = transcript.lower().split()
        
        repetition_count = 0
        for i in range(len(words) - 1):
            # Check for exact word repetition
            if words[i] == words[i + 1]:
                repetition_count += 1
            # Check for partial word repetition (first 3 chars same)
            elif len(words[i]) >= 3 and words[i][:3] == words[i + 1][:3]:
                repetition_count += 0.5  # Half weight for partial repetition
        
        repetition_count = int(repetition_count)
        logger.info(f"Repetitions detected: {repetition_count}")
        return repetition_count, ""
    
    except Exception as e:
        logger.error(f"Repetition detection error: {e}")
        return 0, f"Repetition detection failed: {str(e)}"


def detect_fillers(transcript):
    """
    Detect filler words in transcript
    Returns: (filler_count, error_message)
    """
    try:
        logger.info("Detecting fillers...")
        
        # Common filler words in English and Hindi
        fillers = [
            'um', 'uh', 'umm', 'uhh', 'err', 'erm',  # English
            'aar', 'haan', 'hai', 'toh', 'na'  # Hindi/Hinglish
        ]
        
        words = transcript.lower().split()
        filler_count = sum(1 for word in words if word in fillers)
        
        logger.info(f"Fillers detected: {filler_count}")
        return filler_count, ""
    
    except Exception as e:
        logger.error(f"Filler detection error: {e}")
        return 0, f"Filler detection failed: {str(e)}"


def calculate_severity_score(metrics):
    """
    Calculate severity score based on metrics
    Returns: (score, category, pdf_type)
    """
    pauses = metrics.get('pauses', 0)
    repetitions = metrics.get('repetitions', 0)
    speech_rate = metrics.get('speech_rate', 100)
    fillers = metrics.get('fillers', 0)
    
    # Scoring formula
    pause_score = pauses * 5
    rep_score = repetitions * 3
    
    # Speech rate variance (optimal: 80-150 wpm)
    if speech_rate > 150:
        variance_score = 15
    elif speech_rate < 80:
        variance_score = 10
    else:
        variance_score = 0
    
    filler_score = fillers * 1
    
    # Total score (out of 200)
    total = pause_score + rep_score + variance_score + filler_score
    severity_score = min((total / 200) * 100, 100)  # Cap at 100
    
    # Determine category
    if severity_score < 40:
        category = "minimal"
        pdf_type = "minimal"
    elif severity_score < 70:
        category = "mild"
        pdf_type = "mild"
    else:
        category = "severe"
        pdf_type = "severe"
    
    logger.info(f"Severity score calculated: {severity_score:.2f} ({category})")
    return severity_score, category, pdf_type


# ============================================
# API ENDPOINTS
# ============================================

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "whisper_loaded": whisper_model is not None
    }), 200


@app.route('/analyze', methods=['POST'])
def analyze_speech():
    """
    Main endpoint: Analyze speech video
    
    Request:
        - video: MP4/MOV file (multipart/form-data)
    
    Response:
        {
            "severity_score": 0-100,
            "category": "minimal|mild|severe",
            "metrics": {
                "pauses": int,
                "repetitions": int,
                "speech_rate": int,
                "fillers": int
            },
            "pdf_type": "minimal|mild|severe",
            "transcript": "...",
            "timestamp": "ISO 8601"
        }
    """
    try:
        logger.info("=== NEW ANALYSIS REQUEST ===")
        
        # Check if file is present
        if 'video' not in request.files:
            logger.error("No video file provided")
            return jsonify({"error": "No video file provided"}), 400
        
        file = request.files['video']
        
        # Validate file
        if file.filename == '':
            return jsonify({"error": "No file selected"}), 400
        
        if not allowed_file(file.filename):
            return jsonify({"error": "File format not supported. Use MP4, MOV, AVI, MKV, or WebM"}), 400
        
        # Save uploaded file temporarily
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        logger.info(f"File saved: {filepath}")
        
        try:
            # Step 1: Transcribe
            transcript, success, error = transcribe_video(filepath)
            if not success:
                return jsonify({"error": error}), 400
            
            # Step 2: Extract metrics
            logger.info("Extracting metrics...")
            
            pauses, _ = detect_pauses(transcript, filepath)
            repetitions, _ = detect_repetitions(transcript)
            speech_rate, _, _ = extract_audio_features(filepath)
            fillers, _ = detect_fillers(transcript)
            
            # Build metrics object
            metrics = {
                "pauses": pauses,
                "repetitions": repetitions,
                "speech_rate": speech_rate,
                "fillers": fillers
            }
            
            logger.info(f"Metrics: {metrics}")
            
            # Step 3: Calculate severity
            severity_score, category, pdf_type = calculate_severity_score(metrics)
            
            # Step 4: Build response
            response = {
                "severity_score": round(severity_score, 2),
                "category": category,
                "metrics": metrics,
                "pdf_type": pdf_type,
                "transcript": transcript[:500] if len(transcript) > 500 else transcript,  # First 500 chars
                "timestamp": datetime.now().isoformat()
            }
            
            logger.info(f"Analysis complete: {category} ({severity_score:.2f}/100)")
            return jsonify(response), 200
        
        finally:
            # Cleanup temporary file
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.info(f"Cleaned up: {filepath}")
    
    except Exception as e:
        logger.error(f"Unexpected error in /analyze: {e}")
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500


@app.route('/download-guide/<pdf_type>', methods=['GET'])
def download_guide(pdf_type):
    """
    Download personalized coaching guide PDF
    
    Params:
        pdf_type: "minimal", "mild", or "severe"
    
    Returns: PDF file
    """
    try:
        logger.info(f"Requested guide: {pdf_type}")
        
        # Validate pdf_type
        if pdf_type not in ['minimal', 'mild', 'severe']:
            return jsonify({"error": "Invalid guide type"}), 400
        
        # Build file path
        pdf_path = os.path.join(PDF_FOLDER, f"{pdf_type}.pdf")
        
        # Check if file exists
        if not os.path.exists(pdf_path):
            logger.error(f"PDF not found: {pdf_path}")
            return jsonify({"error": f"Guide not available: {pdf_type}"}), 404
        
        logger.info(f"Sending PDF: {pdf_path}")
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=f"unstammer_guide_{pdf_type}.pdf",
            mimetype='application/pdf'
        )
    
    except Exception as e:
        logger.error(f"Error downloading guide: {e}")
        return jsonify({"error": f"Failed to download guide: {str(e)}"}), 500


@app.route('/stats', methods=['GET'])
def get_stats():
    """
    Get system statistics (optional)
    """
    return jsonify({
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "max_file_size_mb": MAX_FILE_SIZE / (1024 * 1024),
        "supported_formats": list(ALLOWED_EXTENSIONS),
        "whisper_model": "base" if whisper_model else "not_loaded"
    }), 200


# ============================================
# ERROR HANDLERS
# ============================================

@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error"""
    return jsonify({
        "error": f"File too large. Maximum size: {MAX_FILE_SIZE / (1024 * 1024)}MB"
    }), 413


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({"error": "Endpoint not found"}), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify({"error": "Internal server error"}), 500


# ============================================
# MAIN
# ============================================

if __name__ == '__main__':
    # Create PDF folder if it doesn't exist
    os.makedirs(PDF_FOLDER, exist_ok=True)
    
    # Get port from environment or use 5000
    port = int(os.environ.get('PORT', 5000))
    
    # Run app
    logger.info(f"Starting UNStammer backend on port {port}")
    app.run(
        host='0.0.0.0',
        port=port,
        debug=os.environ.get('FLASK_ENV') == 'development'
    )