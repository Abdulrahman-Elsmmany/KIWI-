"""
Main CLI interface for the Kiwi TTS application.

This module provides the Click-based command-line interface for converting
text documents to speech using Google Cloud TTS Chirp 3 HD voices.
"""

from pathlib import Path
from typing import Optional

import click

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


@click.command()
@click.argument('file_path', type=click.Path(exists=True, path_type=Path))
@click.option(
    '--voice', 
    default="en-US-Chirp3-HD-Charon",
    help='Chirp 3 HD voice name (e.g., en-US-Chirp3-HD-Charon, en-US-Chirp3-HD-Kore)'
)
@click.option(
    '--output', 
    type=click.Path(path_type=Path),
    help='Output audio file path (default: auto-generated based on input filename)'
)
@click.option(
    '--format', 
    'audio_format',
    type=click.Choice(['MP3', 'LINEAR16'], case_sensitive=False),
    default='MP3',
    help='Audio output format'
)
@click.option(
    '--language',
    default="en-US",
    help='Language code for TTS synthesis'
)
@click.option(
    '--list-voices',
    is_flag=True,
    help='List available Chirp 3 HD voices for the specified language'
)
@click.option(
    '--verbose', '-v',
    is_flag=True,
    help='Enable verbose output'
)
def cli(
    file_path: Path,
    voice: str,
    output: Optional[Path],
    audio_format: str,
    language: str,
    list_voices: bool,
    verbose: bool
) -> None:
    """
    Convert text documents to speech using Google Cloud TTS Chirp 3 HD voices.
    
    Kiwi supports Markdown (.md) and plain text (.txt) files, converting them
    to high-quality speech audio files.
    
    Examples:
    
    \b
        # Convert a Markdown file with default settings
        kiwi document.md
        
        # Use a specific voice and output format
        kiwi document.md --voice en-US-Chirp3-HD-Kore --format LINEAR16
        
        # Specify custom output path
        kiwi document.txt --output /path/to/output.mp3
        
        # List available voices
        kiwi --list-voices document.md
    """
    
    # Handle list voices option
    if list_voices:
        voices = TTSClient.list_available_voices(language)
        click.echo(f"Available Chirp 3 HD voices for {language}:")
        for voice_name in voices:
            click.echo(f"  {voice_name}")
        return
    
    try:
        # Fast startup - validate inputs first
        if verbose:
            click.echo(f"🔍 Validating input file: {file_path}")
        
        validate_input_file(file_path)
        
        # Generate output path if not provided
        if output is None:
            audio_fmt = AudioFormat[audio_format.upper()]
            output = generate_output_path(file_path, audio_format=audio_fmt)
            if verbose:
                click.echo(f"📁 Generated output path: {output}")
        
        # Initialize TTS configuration
        config = TTSConfig(
            voice_name=voice,
            language_code=language,
            audio_encoding=AudioFormat[audio_format.upper()]
        )
        
        if verbose:
            click.echo(f"🎤 Using voice: {voice}")
            click.echo(f"🔊 Audio format: {audio_format}")
        
        # Determine parser based on file extension
        parser = ParserFactory.get_parser(file_path.suffix)
        if verbose:
            click.echo(f"📄 Using parser: {parser.__class__.__name__}")
        
        # Show progress for user feedback
        with click.progressbar(
            length=100, 
            label="Processing document",
            show_percent=True,
            show_eta=False  # Disable ETA for cleaner output
        ) as bar:
            # Parse document
            if verbose:
                click.echo("\n📖 Parsing document...")
            text = parser.parse(file_path)
            bar.update(25)
            
            if verbose:
                text_preview = text[:100] + "..." if len(text) > 100 else text
                click.echo(f"📝 Extracted text ({len(text)} chars): {text_preview}")
            
            # Initialize TTS client
            if verbose:
                click.echo("🔐 Initializing TTS client...")
            tts_client = TTSClient(config)
            bar.update(15)
            
            # Synthesize speech
            if verbose:
                click.echo("🎵 Synthesizing speech...")
            
            # Update progress in smaller increments during synthesis
            bar.update(10)  # Now at 50%
            result = tts_client.synthesize(text, output)
            bar.update(50)  # Complete to 100%
        
        # Report results
        if result.success:
            click.echo(f"✅ Audio generated successfully: {result.output_file}")
            if verbose and result.duration_seconds:
                click.echo(f"⏱️  Processing time: {result.duration_seconds:.2f} seconds")
                
                # Estimate audio duration (rough calculation)
                # Average speaking rate is ~150 words per minute
                word_count = len(text.split())
                estimated_duration = word_count / 150 * 60  # seconds
                click.echo(f"🎧 Estimated audio duration: {estimated_duration:.1f} seconds")
        else:
            click.echo(f"❌ Synthesis failed: {result.error_message}", err=True)
            raise click.Abort()
    
    except FileValidationError as e:
        click.echo(f"❌ File validation error: {e}", err=True)
        raise click.Abort()
    
    except TextTooLongError as e:
        click.echo(f"❌ Text too long: {e}", err=True)
        click.echo(
            "💡 Tip: Split large documents into smaller sections or use a different TTS service.",
            err=True
        )
        raise click.Abort()
    
    except TTSAuthenticationError as e:
        click.echo(f"❌ Authentication error: {e}", err=True)
        click.echo("\n🔧 Troubleshooting steps:")
        click.echo("1. Install Google Cloud CLI: https://cloud.google.com/sdk/docs/install")
        click.echo("2. Run: gcloud auth application-default login")
        click.echo("3. Enable Text-to-Speech API: gcloud services enable texttospeech.googleapis.com")
        click.echo("4. Ensure your project has billing enabled")
        raise click.Abort()
    
    except KiwiError as e:
        click.echo(f"❌ Error: {e}", err=True)
        raise click.Abort()
    
    except Exception as e:
        if verbose:
            import traceback
            click.echo(f"❌ Unexpected error: {e}", err=True)
            click.echo("Full traceback:", err=True)
            click.echo(traceback.format_exc(), err=True)
        else:
            click.echo(f"❌ Unexpected error: {e}", err=True)
            click.echo("Use --verbose for detailed error information.", err=True)
        raise click.Abort()


@click.group()
def main() -> None:
    """Kiwi - Desktop Text-to-Speech Application."""
    pass


# Add the CLI command as the default command
main.add_command(cli)


@main.command()
@click.option('--language', default="en-US", help='Language code')
def voices(language: str) -> None:
    """List available Chirp 3 HD voices."""
    try:
        voices_list = TTSClient.list_available_voices(language)
        click.echo(f"Available Chirp 3 HD voices for {language}:")
        for voice in voices_list:
            # Extract just the voice name part for cleaner display
            voice_name = voice.split('-Chirp3-HD-')[-1]
            click.echo(f"  {voice_name} ({voice})")
    except Exception as e:
        click.echo(f"❌ Error listing voices: {e}", err=True)


@main.command()
@click.option('--host', default="127.0.0.1", help='Host to bind to')
@click.option('--port', default=8000, help='Port to bind to')
@click.option('--reload', is_flag=True, help='Enable auto-reload for development')
def server(host: str, port: int, reload: bool) -> None:
    """Start the Kiwi TTS API server."""
    try:
        from .api import start_server
        click.echo(f"🚀 Starting Kiwi TTS API server on http://{host}:{port}")
        if reload:
            click.echo("🔄 Auto-reload enabled for development")
        start_server(host=host, port=port, reload=reload)
    except ImportError as e:
        click.echo(f"❌ Failed to import API server: {e}", err=True)
        click.echo("💡 Make sure FastAPI dependencies are installed: uv add fastapi uvicorn[standard]")
        raise click.Abort()
    except Exception as e:
        click.echo(f"❌ Failed to start server: {e}", err=True)
        raise click.Abort()


if __name__ == '__main__':
    main()