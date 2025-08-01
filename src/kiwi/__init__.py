"""
Kiwi Desktop TTS Application.

A fast, simple desktop text-to-speech application using Google Cloud TTS Chirp 3 HD voices.
"""

__version__ = "0.1.0"
__author__ = "Kiwi Developer"

from .main import cli
from .tts import TTSClient
from .parsers import MarkdownParser, TextFileParser

__all__ = ["cli", "TTSClient", "MarkdownParser", "TextFileParser"]