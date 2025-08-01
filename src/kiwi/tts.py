"""
Google Cloud Text-to-Speech client for Kiwi application.

This module provides the TTSClient class for converting text to speech using
Google Cloud TTS Chirp 3 HD voices.
"""

import time
from pathlib import Path
from typing import Optional
from dataclasses import dataclass

from dotenv import load_dotenv
from google.cloud import texttospeech
from google.auth.exceptions import DefaultCredentialsError

from .utils import (
    AudioFormat,
    TTSAuthenticationError,
    validate_text_length,
    ensure_directory_exists,
)


# Available Chirp 3 HD voices (verified from Google Cloud documentation)
CHIRP_3_HD_VOICES = [
    "Achernar", "Achird", "Algenib", "Algieba", "Alnilam", "Aoede", "Autonoe",
    "Callirrhoe", "Charon", "Despina", "Enceladus", "Erinome", "Fenrir", "Gacrux",
    "Iapetus", "Kore", "Laomedeia", "Leda", "Orus", "Pulcherrima", "Puck",
    "Rasalgethi", "Sadachbia", "Sadaltager", "Schedar", "Sulafat", "Umbriel",
    "Vindemiatrix", "Zephyr", "Zubenelgenubi"
]


@dataclass
class TTSConfig:
    """Configuration for TTS synthesis."""
    voice_name: str = "en-US-Chirp3-HD-Charon"
    language_code: str = "en-US"
    audio_encoding: AudioFormat = AudioFormat.MP3
    sample_rate: int = 24000


@dataclass
class ProcessingResult:
    """Result of document processing."""
    input_file: Optional[Path] = None
    output_file: Optional[Path] = None
    success: bool = False
    error_message: Optional[str] = None
    duration_seconds: Optional[float] = None


class TTSClient:
    """
    Google Cloud Text-to-Speech client for Chirp 3 HD voices.
    
    This client handles authentication, text validation, and synthesis
    with proper error handling and retry logic.
    """
    
    def __init__(self, config: TTSConfig) -> None:
        """
        Initialize TTS client with authentication handling.
        
        Args:
            config (TTSConfig): Configuration for TTS synthesis.
            
        Raises:
            TTSAuthenticationError: If Google Cloud authentication fails.
        """
        # Load environment variables as required by CLAUDE.md
        load_dotenv()
        
        self.config = config
        
        # Validate voice name format
        self._validate_voice_name(config.voice_name)
        
        # Initialize Google Cloud TTS client with authentication handling
        try:
            self.client = texttospeech.TextToSpeechClient()
        except DefaultCredentialsError as e:
            raise TTSAuthenticationError(
                f"Google Cloud authentication failed: {e}. "
                f"Please run 'gcloud auth application-default login' or set "
                f"GOOGLE_APPLICATION_CREDENTIALS environment variable."
            ) from e
        except Exception as e:
            raise TTSAuthenticationError(
                f"Failed to initialize TTS client: {e}"
            ) from e
    
    def _validate_voice_name(self, voice_name: str) -> None:
        """
        Validate that the voice name follows Chirp 3 HD format.
        
        Args:
            voice_name (str): Voice name to validate.
            
        Raises:
            ValueError: If voice name format is invalid.
        """
        if not voice_name.startswith(self.config.language_code + "-Chirp3-HD-"):
            raise ValueError(
                f"Invalid Chirp 3 HD voice name format: {voice_name}. "
                f"Expected format: {self.config.language_code}-Chirp3-HD-<VoiceName>"
            )
        
        # Extract voice name part
        voice_part = voice_name.split("-Chirp3-HD-")[-1]
        if voice_part not in CHIRP_3_HD_VOICES:
            raise ValueError(
                f"Unknown Chirp 3 HD voice: {voice_part}. "
                f"Available voices: {', '.join(CHIRP_3_HD_VOICES)}"
            )
    
    def synthesize(self, text: str, output_path: Path) -> ProcessingResult:
        """
        Synthesize text to speech using Chirp 3 HD voice.
        
        Args:
            text (str): Text to convert to speech.
            output_path (Path): Path where audio file will be saved.
            
        Returns:
            ProcessingResult: Result of the synthesis operation.
        """
        start_time = time.time()
        
        try:
            # Validate text length (5,000 byte limit for Chirp 3 HD)
            validate_text_length(text)
            
            # Ensure output directory exists
            ensure_directory_exists(output_path)
            
            # Configure voice selection for Chirp 3 HD
            voice = texttospeech.VoiceSelectionParams(
                language_code=self.config.language_code,
                name=self.config.voice_name
            )
            
            # Use text input (Chirp 3 HD doesn't support SSML)
            synthesis_input = texttospeech.SynthesisInput(text=text)
            
            # Configure audio output
            audio_encoding = getattr(
                texttospeech.AudioEncoding, 
                self.config.audio_encoding.value
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=audio_encoding,
                sample_rate_hertz=self.config.sample_rate
            )
            
            # Perform synthesis with retry logic
            response = self._synthesize_with_retry(
                synthesis_input, voice, audio_config
            )
            
            # Write audio content to file (already binary, no base64 decoding needed)
            with open(output_path, "wb") as out:
                out.write(response.audio_content)
            
            duration = time.time() - start_time
            
            return ProcessingResult(
                output_file=output_path,
                success=True,
                duration_seconds=duration
            )
            
        except Exception as e:
            duration = time.time() - start_time
            return ProcessingResult(
                output_file=output_path,
                success=False,
                error_message=str(e),
                duration_seconds=duration
            )
    
    def _synthesize_with_retry(
        self,
        synthesis_input: texttospeech.SynthesisInput,
        voice: texttospeech.VoiceSelectionParams,
        audio_config: texttospeech.AudioConfig,
        max_retries: int = 2,
        base_delay: float = 0.5
    ) -> texttospeech.SynthesizeSpeechResponse:
        """
        Perform synthesis with exponential backoff retry logic.
        
        Args:
            synthesis_input: Text input for synthesis.
            voice: Voice selection parameters.
            audio_config: Audio configuration.
            max_retries: Maximum number of retry attempts.
            base_delay: Base delay between retries in seconds.
            
        Returns:
            SynthesizeSpeechResponse: Response from Google TTS API.
            
        Raises:
            Exception: If all retry attempts fail.
        """
        request = texttospeech.SynthesizeSpeechRequest(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                # Use async-friendly approach
                response = self.client.synthesize_speech(request=request)
                return response
            except Exception as e:
                last_exception = e
                
                if attempt < max_retries:
                    # Reduced delay for faster retries
                    delay = base_delay * (1.5 ** attempt)  # Less aggressive backoff
                    time.sleep(min(delay, 2.0))  # Cap at 2 seconds
                    continue
                else:
                    # Final attempt failed
                    break
        
        # All retries failed
        raise Exception(
            f"TTS synthesis failed after {max_retries + 1} attempts. "
            f"Last error: {last_exception}"
        ) from last_exception
    
    @staticmethod
    def list_available_voices(language_code: str = "en-US") -> list[str]:
        """
        Get list of available Chirp 3 HD voices for a language.
        
        Args:
            language_code (str): Language code (e.g., "en-US").
            
        Returns:
            list[str]: List of available voice names.
        """
        return [f"{language_code}-Chirp3-HD-{voice}" for voice in CHIRP_3_HD_VOICES]