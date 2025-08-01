"""
Utility functions for the Kiwi TTS application.

This module provides file validation, audio output utilities, and error handling helpers.
"""

from pathlib import Path
from typing import Optional
from enum import Enum


class AudioFormat(Enum):
    """Supported audio formats for TTS output."""
    MP3 = "MP3"
    LINEAR16 = "LINEAR16"


class SupportedFileType(Enum):
    """Supported input file types for document parsing."""
    MARKDOWN = ".md"
    TEXT = ".txt"


class KiwiError(Exception):
    """Base exception class for Kiwi application errors."""
    pass


class FileValidationError(KiwiError):
    """Exception raised when file validation fails."""
    pass


class TTSAuthenticationError(KiwiError):
    """Exception raised when Google Cloud TTS authentication fails."""
    pass


class TextTooLongError(KiwiError):
    """Exception raised when text exceeds the 5,000 byte limit for Chirp 3 HD."""
    pass


def validate_input_file(file_path: Path) -> Path:
    """
    Validate that the input file exists and is a supported format.

    Args:
        file_path (Path): Path to the input file to validate.

    Returns:
        Path: The validated file path.

    Raises:
        FileValidationError: If file doesn't exist or is unsupported format.
    """
    if not file_path.exists():
        raise FileValidationError(f"File does not exist: {file_path}")
    
    if not file_path.is_file():
        raise FileValidationError(f"Path is not a file: {file_path}")
    
    supported_extensions = {ext.value for ext in SupportedFileType}
    if file_path.suffix.lower() not in supported_extensions:
        raise FileValidationError(
            f"Unsupported file type: {file_path.suffix}. "
            f"Supported types: {', '.join(supported_extensions)}"
        )
    
    return file_path


def validate_text_length(text: str) -> str:
    """
    Validate that text doesn't exceed the 5,000 byte limit for Chirp 3 HD.

    Args:
        text (str): Text to validate.

    Returns:
        str: The validated text.

    Raises:
        TextTooLongError: If text exceeds 5,000 bytes when encoded as UTF-8.
    """
    text_bytes = text.encode('utf-8')
    max_bytes = 5000
    
    if len(text_bytes) > max_bytes:
        raise TextTooLongError(
            f"Text too long: {len(text_bytes)} bytes (max {max_bytes} bytes). "
            f"Consider splitting the document into smaller sections."
        )
    
    return text


def generate_output_path(input_path: Path, output_dir: Optional[Path] = None, 
                        audio_format: AudioFormat = AudioFormat.MP3) -> Path:
    """
    Generate an output file path for the audio file.

    Args:
        input_path (Path): Path to the input document.
        output_dir (Path, optional): Directory for output file. Defaults to same as input.
        audio_format (AudioFormat): Audio format for the output file.

    Returns:
        Path: Generated output file path.
    """
    if output_dir is None:
        output_dir = input_path.parent
    
    # Generate output filename based on input filename
    base_name = input_path.stem
    extension = "mp3" if audio_format == AudioFormat.MP3 else "wav"
    output_filename = f"{base_name}_tts.{extension}"
    
    return output_dir / output_filename


def ensure_directory_exists(file_path: Path) -> None:
    """
    Ensure the parent directory of a file path exists.

    Args:
        file_path (Path): File path whose parent directory should exist.
    """
    file_path.parent.mkdir(parents=True, exist_ok=True)