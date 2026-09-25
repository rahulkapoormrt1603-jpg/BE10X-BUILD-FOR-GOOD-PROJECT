import React, { useState } from 'react';
import axios from 'axios';
import './App.css';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:5000';

export default function App() {
  const [stage, setStage] = useState('upload'); // 'upload' | 'loading' | 'results'
  const [file, setFile] = useState(null);
  const [fileName, setFileName] = useState('');
  const [results, setResults] = useState(null);
  const [error, setError] = useState('');
  const [uploading, setUploading] = useState(false);

  // Validate file
  const validateFile = (selectedFile) => {
    if (!selectedFile) {
      setError('Please select a file');
      return false;
    }

    const validTypes = ['video/mp4', 'video/quicktime'];
    if (!validTypes.includes(selectedFile.type)) {
      setError('Please upload an MP4 or MOV file');
      return false;
    }

    const maxSize = 100 * 1024 * 1024; // 100MB
    if (selectedFile.size > maxSize) {
      setError('File size must be less than 100MB');
      return false;
    }

    return true;
  };

  // Handle file selection
  const handleFileChange = (e) => {
    const selectedFile = e.target.files[0];
    setError('');
    
    if (validateFile(selectedFile)) {
      setFile(selectedFile);
      setFileName(selectedFile.name);
    }
  };

  // Submit video for analysis
  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!file) {
      setError('Please select a video file');
      return;
    }

    setUploading(true);
    setError('');
    setStage('loading');

    try {
      const formData = new FormData();
      formData.append('video', file);

      const response = await axios.post(
        `${API_BASE_URL}/analyze`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
          timeout: 600000, // 10 minutes for long video processing
        }
      );

      if (response.status === 200 && response.data) {
        setResults(response.data);
        setStage('results');
      }
    } catch (err) {
      let errorMsg = 'Failed to analyze video. Please try again.';
      
      if (err.response?.status === 413) {
        errorMsg = 'File is too large. Maximum 100MB allowed.';
      } else if (err.response?.status === 400) {
        errorMsg = err.response.data.error || 'Invalid video format or file corrupted.';
      } else if (err.response?.status === 408 || err.code === 'ECONNABORTED') {
        errorMsg = 'Analysis took too long. Please try a shorter video.';
      } else if (err.message === 'Network Error') {
        errorMsg = 'Unable to connect to server. Make sure backend is running.';
      }
      
      setError(errorMsg);
      setStage('upload');
    } finally {
      setUploading(false);
    }
  };

  // Download PDF guide
  const handleDownloadPDF = async (pdfType) => {
    try {
      const response = await axios.get(
        `${API_BASE_URL}/download-guide/${pdfType}`,
        {
          responseType: 'blob',
        }
      );

      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `unstammer_guide_${pdfType}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.parentChild?.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      setError('Failed to download PDF. Please try again.');
    }
  };

  // Get category color
  const getCategoryColor = (score) => {
    if (score < 40) return '#10b981'; // green - minimal
    if (score < 70) return '#f59e0b'; // amber - mild
    return '#ef4444'; // red - severe
  };

  // Get category text
  const getCategoryText = (score) => {
    if (score < 40) return 'Minimal';
    if (score < 70) return 'Mild';
    return 'Severe';
  };

  // Render upload stage
  const renderUpload = () => (
    <div className="stage-container">
      <div className="upload-section">
        <div className="icon-large">🎥</div>
        <h2>Upload Your Speech Video</h2>
        <p className="subtitle">Analyze your speech patterns in just 60 seconds</p>

        <form onSubmit={handleSubmit} className="upload-form">
          <div className="file-input-wrapper">
            <input
              type="file"
              id="video-input"
              accept=".mp4,.mov,video/mp4,video/quicktime"
              onChange={handleFileChange}
              disabled={uploading}
              className="file-input"
            />
            <label htmlFor="video-input" className="file-label">
              <span className="upload-icon">📁</span>
              <span className="upload-text">
                {fileName || 'Click to select or drag video here'}
              </span>
              <span className="upload-hint">MP4 or MOV • Max 100MB</span>
            </label>
          </div>

          {error && <div className="error-banner">{error}</div>}

          <button
            type="submit"
            disabled={!file || uploading}
            className="btn btn-primary btn-large"
          >
            {uploading ? '⏳ Analyzing...' : '▶ Analyze Video'}
          </button>
        </form>

        <div className="info-cards">
          <div className="info-card">
            <span className="icon">⚡</span>
            <p><strong>Fast:</strong> Analysis in 60 seconds</p>
          </div>
          <div className="info-card">
            <span className="icon">🔒</span>
            <p><strong>Private:</strong> Your video is not stored</p>
          </div>
          <div className="info-card">
            <span className="icon">📊</span>
            <p><strong>Detailed:</strong> Comprehensive speech metrics</p>
          </div>
        </div>
      </div>
    </div>
  );

  // Render loading stage
  const renderLoading = () => (
    <div className="stage-container loading-stage">
      <div className="spinner"></div>
      <h2>Analyzing Your Speech...</h2>
      <p className="subtitle">Please wait while we process your video</p>
      <div className="progress-steps">
        <div className="step active">✓ Transcription</div>
        <div className="step active">✓ Pattern Detection</div>
        <div className="step">⏳ Scoring</div>
      </div>
    </div>
  );

  // Render results stage
  const renderResults = () => {
    if (!results) return null;

    const score = results.severity_score || 0;
    const category = results.category || getCategoryText(score);
    const pdfType = results.pdf_type || (score < 40 ? 'minimal' : score < 70 ? 'mild' : 'severe');
    const metrics = results.metrics || {};

    return (
      <div className="stage-container">
        <div className="results-section">
          {/* Score Card */}
          <div className="score-card" style={{ borderLeftColor: getCategoryColor(score) }}>
            <div className="score-header">
              <h2>Your Speech Assessment</h2>
              <button
                className="btn-back"
                onClick={() => {
                  setStage('upload');
                  setFile(null);
                  setFileName('');
                  setResults(null);
                  setError('');
                }}
                title="Analyze another video"
              >
                ← New Analysis
              </button>
            </div>

            <div className="score-visualization">
              <div className="score-circle" style={{ borderColor: getCategoryColor(score) }}>
                <div className="score-value">{Math.round(score)}</div>
                <div className="score-max">/100</div>
              </div>
              <div className="score-info">
                <div className="category-badge" style={{ backgroundColor: getCategoryColor(score) }}>
                  {category}
                </div>
                <p className="score-description">
                  {score < 40 && 'Your speech is relatively fluent with minimal stuttering patterns.'}
                  {score >= 40 && score < 70 && 'Your speech shows moderate stuttering. Coaching can help significantly.'}
                  {score >= 70 && 'Your speech shows significant stuttering. Professional coaching is recommended.'}
                </p>
              </div>
            </div>
          </div>

          {/* Metrics */}
          <div className="metrics-card">
            <h3>Speech Metrics</h3>
            <div className="metrics-grid">
              <div className="metric">
                <span className="metric-icon">⏸️</span>
                <div className="metric-content">
                  <span className="metric-label">Pauses</span>
                  <span className="metric-value">{metrics.pauses || 0}</span>
                  <span className="metric-hint">Extended silence</span>
                </div>
              </div>
              <div className="metric">
                <span className="metric-icon">🔄</span>
                <div className="metric-content">
                  <span className="metric-label">Repetitions</span>
                  <span className="metric-value">{metrics.repetitions || 0}</span>
                  <span className="metric-hint">Stuttering blocks</span>
                </div>
              </div>
              <div className="metric">
                <span className="metric-icon">⚡</span>
                <div className="metric-content">
                  <span className="metric-label">Speech Rate</span>
                  <span className="metric-value">{metrics.speech_rate || 0} wpm</span>
                  <span className="metric-hint">Words per minute</span>
                </div>
              </div>
              <div className="metric">
                <span className="metric-icon">🗣️</span>
                <div className="metric-content">
                  <span className="metric-label">Fillers</span>
                  <span className="metric-value">{metrics.fillers || 0}</span>
                  <span className="metric-hint">Um, uh, aar, haan</span>
                </div>
              </div>
            </div>
          </div>

          {/* Guidance */}
          <div className="guidance-card">
            <h3>Next Steps</h3>
            {score < 40 && (
              <div className="guidance-content">
                <p>Your speech is relatively fluent. To maintain and improve further:</p>
                <ul>
                  <li>Practice daily breathing exercises (10-15 min)</li>
                  <li>Record yourself weekly to track progress</li>
                  <li>Download our 6-month Minimal Coaching Guide</li>
                </ul>
              </div>
            )}
            {score >= 40 && score < 70 && (
              <div className="guidance-content">
                <p>Coaching can help significantly. Our proven approach includes:</p>
                <ul>
                  <li>Breathing & vocal training (twice daily)</li>
                  <li>Subconscious rewiring techniques</li>
                  <li>Download our 9-month Mild Coaching Guide for personalized exercises</li>
                </ul>
              </div>
            )}
            {score >= 70 && (
              <div className="guidance-content">
                <p>Professional coaching is recommended. Our intensive program provides:</p>
                <ul>
                  <li>Daily guided sessions & exercises (50+ min/day)</li>
                  <li>Expert speech therapist consultation</li>
                  <li>Download our 12-month Severe Coaching Guide</li>
                </ul>
              </div>
            )}
          </div>

          {/* Download Button */}
          <button
            className="btn btn-primary btn-large"
            onClick={() => handleDownloadPDF(pdfType)}
          >
            📥 Download Your {category} Coaching Guide
          </button>

          {error && <div className="error-banner">{error}</div>}
        </div>
      </div>
    );
  };

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-content">
          <div className="logo">
            <span className="logo-icon">🎤</span>
            <span className="logo-text">UNStammer</span>
          </div>
          <p className="tagline">A clearer way to hear yourself</p>
        </div>
      </header>

      {/* Main Content */}
      <main className="main-content">
        {stage === 'upload' && renderUpload()}
        {stage === 'loading' && renderLoading()}
        {stage === 'results' && renderResults()}
      </main>

      {/* Footer */}
      <footer className="footer">
        <p>UNStammer © 2026 • Built for speech fluency assessment</p>
        <p style={{ 
          fontSize: '12px', 
          color: '#6b7280', 
          marginTop: '8px', 
          lineHeight: '1.5',
          maxWidth: '600px',
          marginLeft: 'auto',
          marginRight: 'auto'
        }}>
          <strong>⚠ Important:</strong> If your stammering is very severe and is hurting your body and mind physically or mentally, we strongly recommend you visit an appropriate speech therapist and doctors for proper guidance and medical evaluation.
        </p>
      </footer>
    </div>
  );
}