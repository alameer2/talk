# Overview

This is a Python-based SRT (subtitle) to Arabic speech converter application. The project converts subtitle files into synchronized Arabic audio, maintaining precise timing for each subtitle line. It features a Streamlit web interface that allows users to upload SRT files and generate audio output with various text-to-speech engines. The application is designed to work both online (using cloud TTS services) and offline (using local TTS engines).

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture

**Web Interface**: Built with Streamlit for an interactive, user-friendly experience
- Single-page application with wide layout configuration
- Real-time progress tracking during conversion
- File upload support (direct upload or from `upload` folder)
- User preference persistence via JSON storage
- RTL (right-to-left) support for Arabic text display

## Backend Architecture

**Modular Design**: The application follows a separation of concerns pattern with distinct modules:

1. **SRT Processing Module** (`srt_processor.py`)
   - Uses `pysrt` library for parsing subtitle files
   - Extracts timing information (start/end times) and text content
   - Converts timestamps to seconds for processing
   - Cleans and normalizes subtitle text

2. **Text Processing Module** (`text_processor.py`)
   - Handles Arabic text reshaping and bidirectional text (using `arabic-reshaper` and `python-bidi`)
   - Manages punctuation-based pause timing
   - Optional text vocalization support (using `mishkal`)
   - Converts between Arabic and Western numerals
   - Punctuation pause mapping for natural speech rhythm

3. **TTS Engine Module** (`tts_engine.py`)
   - Multi-engine support with graceful fallbacks:
     - **gTTS**: Free Google TTS (requires internet)
     - **pyttsx3**: Local offline TTS
     - **Azure Cognitive Services**: Enterprise-grade cloud TTS
     - **ElevenLabs**: High-quality AI voice synthesis
     - **AWS Polly**: Amazon's text-to-speech service
   - Configurable speech rate and quality settings
   - API key management for cloud services

4. **Audio Utilities Module** (`audio_utils.py`)
   - Audio file manipulation using `pydub`
   - Silence generation for timing synchronization
   - Audio segment concatenation
   - Pause insertion between subtitle segments
   - ZIP archive creation for batch downloads

5. **Main Application** (`app.py`)
   - Orchestrates all modules
   - Manages application state and user sessions
   - Handles file I/O operations
   - Implements user preference persistence

**Design Patterns**:
- **Modular Architecture**: Each module has a single responsibility
- **Graceful Degradation**: Optional dependencies are handled with try-except imports and availability flags
- **Error Handling**: Comprehensive logging throughout all modules
- **Configuration Management**: User preferences stored in JSON format

## Data Storage

**File-Based Storage**:
- **Input**: `upload/` directory for SRT files
- **Output**: `output/` directory for generated audio files
- **Temporary Files**: `temp/` directory for processing
- **User Preferences**: `user_preferences.json` for persistent settings

No traditional database is used; the application relies on filesystem operations for data management. This approach was chosen for simplicity and to avoid infrastructure dependencies.

## Authentication and Authorization

No authentication system is implemented. The application is designed as a single-user tool that can be deployed per-user on platforms like Replit or run locally.

# External Dependencies

## Core Python Libraries

- **streamlit**: Web application framework (UI layer)
- **pysrt**: SRT subtitle file parsing
- **pydub**: Audio file manipulation and processing
- **arabic-reshaper**: Arabic text reshaping for proper display
- **python-bidi**: Bidirectional text support

## Text-to-Speech Engines

1. **gTTS** (Google Text-to-Speech)
   - Free, cloud-based
   - Requires internet connection
   - No API key needed

2. **pyttsx3**
   - Local, offline TTS engine
   - No external dependencies
   - Works without internet

3. **Azure Cognitive Services** (Optional)
   - Enterprise cloud TTS
   - Requires API key and region configuration
   - High-quality voices

4. **ElevenLabs** (Optional)
   - AI-powered voice synthesis
   - Requires API key
   - Premium quality output

5. **AWS Polly** (Optional)
   - Amazon's TTS service
   - Requires AWS credentials
   - Multiple voice options

## Optional Enhancement Libraries

- **mishkal**: Arabic text vocalization (diacritization)
- **boto3**: AWS SDK for Polly integration
- **azure-cognitiveservices-speech**: Azure TTS SDK

## Platform Requirements

- Python 3.11 or newer
- Internet connection (for cloud TTS services)
- FFmpeg (required by pydub for audio processing)

## Deployment Platforms

Designed to run on:
- **Replit**: Auto-configuration via `.replit` and `replit.nix`
- **Local Development**: Via pip or uv package manager
- Any Python-capable hosting environment