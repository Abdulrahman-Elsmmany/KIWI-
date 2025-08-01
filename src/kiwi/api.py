"""
FastAPI web server for Kiwi TTS application.

This module provides a REST API interface for the TTS functionality,
allowing the Tauri GUI to make HTTP requests instead of CLI calls.
"""

import tempfile
import time
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

from .tts import TTSClient, TTSConfig
from .parsers import ParserFactory
from .utils import (
    AudioFormat,
    validate_input_file,
    generate_output_path,
    KiwiError,
    TTSAuthenticationError,
    FileValidationError,
    TextTooLongError,
)


# Pydantic models for API requests/responses
class Voice(BaseModel):
    """Voice information model."""
    name: str
    language_code: str
    ssml_gender: str
    display_name: Optional[str] = None


class VoicesResponse(BaseModel):
    """Response model for voices endpoint."""
    voices: List[Voice]
    language_code: str


class TTSRequest(BaseModel):
    """Request model for text-to-speech conversion."""
    text: str
    voice: str
    format: str = "MP3"
    language: str = "en-US"


class TTSResponse(BaseModel):
    """Response model for text-to-speech conversion."""
    success: bool
    output_path: Optional[str] = None
    file_size: Optional[str] = None
    processing_time: Optional[str] = None
    error: Optional[str] = None
    download_url: Optional[str] = None


# FastAPI app instance
app = FastAPI(
    title="Kiwi TTS API",
    description="Text-to-Speech API using Google Cloud TTS Chirp 3 HD voices",
    version="1.0.0"
)

# Configure CORS for Tauri app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://tauri.localhost"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global TTS client instance (initialized on first use)
_tts_client: Optional[TTSClient] = None
_temp_files: dict = {}  # Track temporary files for cleanup


def get_tts_client(config: TTSConfig) -> TTSClient:
    """
    Get or create TTS client instance.
    
    Args:
        config: TTS configuration
        
    Returns:
        TTSClient: Initialized TTS client
    """
    global _tts_client
    if _tts_client is None or _tts_client.config != config:
        _tts_client = TTSClient(config)
    return _tts_client


@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Kiwi TTS API",
        "version": "1.0.0",
        "endpoints": {
            "voices": "/voices/{language_code}",
            "synthesize": "/synthesize",
            "download": "/download/{file_id}"
        }
    }


@app.get("/voices/{language_code}", response_model=VoicesResponse)
async def get_voices(language_code: str = "en-US"):
    """
    Get available voices for a language.
    
    Args:
        language_code: Language code (e.g., "en-US")
        
    Returns:
        VoicesResponse: List of available voices
    """
    try:
        voice_names = TTSClient.list_available_voices(language_code)
        
        # Convert to Voice objects with gender information
        voices = []
        female_voices = {"Charon", "Kore", "Leda", "Aoede", "Callirrhoe", "Pulcherrima", "Despina"}
        
        for voice_name in voice_names:
            # Extract just the voice name part
            display_name = voice_name.split('-Chirp3-HD-')[-1]
            gender = "FEMALE" if display_name in female_voices else "MALE"
            
            voices.append(Voice(
                name=voice_name,
                language_code=language_code,
                ssml_gender=gender,
                display_name=f"{display_name} (HD)"
            ))
        
        return VoicesResponse(
            voices=voices,
            language_code=language_code
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get voices: {str(e)}")


@app.post("/synthesize", response_model=TTSResponse)
async def synthesize_text(request: TTSRequest):
    """
    Convert text to speech.
    
    Args:
        request: TTS request with text, voice, and options
        
    Returns:
        TTSResponse: Result of synthesis operation
    """
    start_time = time.time()
    
    try:
        # Validate audio format
        try:
            audio_format = AudioFormat[request.format.upper()]
        except KeyError:
            raise HTTPException(
                status_code=400, 
                detail=f"Invalid audio format: {request.format}. Use MP3 or LINEAR16"
            )
        
        # Create TTS configuration
        config = TTSConfig(
            voice_name=request.voice,
            language_code=request.language,
            audio_encoding=audio_format
        )
        
        # Get TTS client
        tts_client = get_tts_client(config)
        
        # Generate output path in temp directory
        temp_dir = Path(tempfile.gettempdir()) / "kiwi_tts"
        temp_dir.mkdir(exist_ok=True)
        
        # Create unique filename
        timestamp = int(time.time() * 1000)
        extension = "mp3" if audio_format == AudioFormat.MP3 else "wav"
        output_path = temp_dir / f"tts_{timestamp}.{extension}"
        
        # Synthesize speech
        result = tts_client.synthesize(request.text, output_path)
        
        processing_time = time.time() - start_time
        
        if result.success:
            # Calculate file size
            file_size = None
            if output_path.exists():
                size_bytes = output_path.stat().st_size
                size_mb = size_bytes / 1_048_576
                file_size = f"{size_mb:.1f} MB"
                
                # Store file info for download
                file_id = f"tts_{timestamp}"
                _temp_files[file_id] = {
                    "path": output_path,
                    "created": time.time()
                }
            
            return TTSResponse(
                success=True,
                output_path=str(output_path),
                file_size=file_size,
                processing_time=f"{processing_time:.2f}s",
                download_url=f"/download/{file_id}" if output_path.exists() else None
            )
        else:
            return TTSResponse(
                success=False,
                error=result.error_message,
                processing_time=f"{processing_time:.2f}s"
            )
            
    except TTSAuthenticationError as e:
        raise HTTPException(status_code=401, detail=str(e))
    except TextTooLongError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        processing_time = time.time() - start_time
        return TTSResponse(
            success=False,
            error=str(e),
            processing_time=f"{processing_time:.2f}s"
        )


@app.post("/synthesize-file", response_model=TTSResponse)
async def synthesize_file(
    file: UploadFile = File(...),
    voice: str = "en-US-Chirp3-HD-Charon",
    format: str = "MP3",
    language: str = "en-US"
):
    """
    Convert uploaded file to speech.
    
    Args:
        file: Uploaded text/markdown file
        voice: Voice name to use
        format: Audio format (MP3 or LINEAR16)
        language: Language code
        
    Returns:
        TTSResponse: Result of synthesis operation
    """
    start_time = time.time()
    
    try:
        # Save uploaded file temporarily
        temp_input = Path(tempfile.gettempdir()) / f"kiwi_input_{int(time.time() * 1000)}{Path(file.filename).suffix}"
        
        with open(temp_input, "wb") as f:
            content = await file.read()
            f.write(content)
        
        try:
            # Validate input file
            validate_input_file(temp_input)
            
            # Parse the file
            parser = ParserFactory.get_parser(temp_input.suffix)
            text = parser.parse(temp_input)
            
            # Use the synthesize_text endpoint logic
            tts_request = TTSRequest(
                text=text,
                voice=voice,
                format=format,
                language=language
            )
            
            return await synthesize_text(tts_request)
            
        finally:
            # Clean up input file
            if temp_input.exists():
                temp_input.unlink()
                
    except FileValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        processing_time = time.time() - start_time
        return TTSResponse(
            success=False,
            error=str(e),
            processing_time=f"{processing_time:.2f}s"
        )


@app.get("/download/{file_id}")
async def download_file(file_id: str):
    """
    Download generated audio file.
    
    Args:
        file_id: File identifier from synthesis response
        
    Returns:
        FileResponse: Audio file download
    """
    if file_id not in _temp_files:
        raise HTTPException(status_code=404, detail="File not found")
    
    file_info = _temp_files[file_id]
    file_path = file_info["path"]
    
    if not file_path.exists():
        # Clean up missing file
        del _temp_files[file_id]
        raise HTTPException(status_code=404, detail="File no longer available")
    
    # Determine media type
    media_type = "audio/mpeg" if file_path.suffix == ".mp3" else "audio/wav"
    
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=file_path.name
    )


@app.delete("/cleanup")
async def cleanup_temp_files():
    """Clean up old temporary files."""
    current_time = time.time()
    cleaned = 0
    
    for file_id in list(_temp_files.keys()):
        file_info = _temp_files[file_id]
        
        # Remove files older than 1 hour
        if current_time - file_info["created"] > 3600:
            file_path = file_info["path"]
            if file_path.exists():
                file_path.unlink()
            del _temp_files[file_id]
            cleaned += 1
    
    return {"cleaned_files": cleaned}


def start_server(host: str = "127.0.0.1", port: int = 8000, reload: bool = False):
    """
    Start the FastAPI server.
    
    Args:
        host: Host to bind to
        port: Port to bind to  
        reload: Enable auto-reload for development
    """
    uvicorn.run("kiwi.api:app", host=host, port=port, reload=reload)


if __name__ == "__main__":
    start_server(reload=True)