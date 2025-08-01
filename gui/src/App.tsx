import { useState } from "react";
import { invoke } from "@tauri-apps/api/core";
import { Mic, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { FileUpload } from "@/components/FileUpload";
import { VoiceSettings } from "@/components/VoiceSettings";
import { ConversionProgress } from "@/components/ConversionProgress";
import { AudioResult } from "@/components/AudioResult";
import "./App.css";

function App() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [language, setLanguage] = useState("en-US");
  const [voice, setVoice] = useState("");
  const [format, setFormat] = useState("MP3");
  const [verboseMode, setVerboseMode] = useState(false);
  const [outputPath, setOutputPath] = useState<string>("");
  const [isConverting, setIsConverting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [progressMessage, setProgressMessage] = useState("");
  const [error, setError] = useState<string | undefined>(undefined);
  const [result, setResult] = useState<{
    audioPath: string;
    fileName: string;
    fileSize: string;
    processingTime: string;
    voiceUsed: string;
  } | null>(null);

  const handleFileSelect = (file: File) => {
    setSelectedFile(file);
    setResult(null);
    setError(undefined);
    setProgress(0);
  };

  const handleClearFile = () => {
    setSelectedFile(null);
    setResult(null);
    setError(undefined);
    setProgress(0);
  };

  const handleStartConversion = async () => {
    if (!selectedFile || !voice) return;

    setIsConverting(true);
    setError(undefined);
    setProgress(0);
    setProgressMessage("Starting conversion...");

    try {
      const startTime = Date.now();
      
      // Read file content
      const text = await selectedFile.text();
      
      // Generate output path
      const fileName = `${selectedFile.name.replace(/\.[^/.]+$/, '')}.${format.toLowerCase()}`;
      const outputFilePath = outputPath ? 
        `${outputPath}/${fileName}` : 
        fileName; // If no output path selected, use current directory or default
      
      // Progress simulation while calling real conversion
      const progressInterval = setInterval(() => {
        setProgress(prev => {
          const newProgress = Math.min(prev + Math.random() * 10, 85);
          if (newProgress < 20) {
            setProgressMessage("Reading file content...");
          } else if (newProgress < 40) {
            setProgressMessage("Connecting to TTS service...");
          } else if (newProgress < 70) {
            setProgressMessage("Generating speech...");
          } else {
            setProgressMessage("Saving audio file...");
          }
          return newProgress;
        });
      }, 300);

      // Call Tauri command for actual conversion
      const conversionResult = await invoke<{
        success: boolean;
        output_path?: string;
        error?: string;
        file_size?: string;
        processing_time?: string;
      }>('convert_text_to_speech', {
        text,
        voice,
        format,
        outputPath: outputFilePath,
        verbose: verboseMode,
      });
      
      clearInterval(progressInterval);
      
      if (!conversionResult.success) {
        throw new Error(conversionResult.error || "Conversion failed");
      }
      
      setProgress(100);
      setProgressMessage("Conversion complete!");
      
      const endTime = Date.now();
      const processingTime = conversionResult.processing_time || `${((endTime - startTime) / 1000).toFixed(1)}s`;
      
      // Set successful result
      setResult({
        audioPath: conversionResult.output_path || outputFilePath,
        fileName: fileName,
        fileSize: conversionResult.file_size || "Unknown size",
        processingTime,
        voiceUsed: voice,
      });
      
    } catch (err) {
      setError(err instanceof Error ? err.message : "Conversion failed");
    } finally {
      setIsConverting(false);
    }
  };

  const handlePlayAudio = () => {
    if (result?.audioPath) {
      // Use native audio element for playback
      const audio = new Audio(result.audioPath);
      audio.play().catch(err => {
        console.error('Failed to play audio:', err);
        // Fallback to opening the file
        handleOpenFile();
      });
    }
  };

  const handleOpenFile = async () => {
    if (result?.audioPath) {
      try {
        await invoke('open_file_path', { path: result.audioPath });
      } catch (error) {
        console.error('Failed to open file:', error);
      }
    }
  };

  const handleOpenFolder = async () => {
    if (result?.audioPath) {
      try {
        await invoke('open_folder_path', { path: result.audioPath });
      } catch (error) {
        console.error('Failed to open folder:', error);
      }
    }
  };

  const handleConvertAnother = () => {
    setSelectedFile(null);
    setResult(null);
    setError(undefined);
    setProgress(0);
    setProgressMessage("");
  };

  const canConvert = selectedFile && voice && !isConverting;

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-muted/20">
      {/* Header */}
      <header className="border-b bg-background/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex size-10 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-primary/80 text-primary-foreground shadow-lg">
                <Mic className="size-5" />
              </div>
              <div>
                <h1 className="text-2xl font-bold bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text text-transparent">
                  Kiwi TTS
                </h1>
                <p className="text-sm text-muted-foreground">Transform text into beautiful speech</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="secondary" className="flex items-center gap-1">
                <Sparkles className="size-3" />
                Premium Quality
              </Badge>
              <Badge variant="outline">30+ Voices</Badge>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto max-w-4xl px-6 py-8">
        <div className="space-y-8">
          {/* File Upload */}
          <FileUpload
            onFileSelect={handleFileSelect}
            selectedFile={selectedFile}
            onClearFile={handleClearFile}
          />

          {/* Voice Settings */}
          <VoiceSettings
            language={language}
            voice={voice}
            format={format}
            verboseMode={verboseMode}
            outputPath={outputPath}
            onLanguageChange={setLanguage}
            onVoiceChange={setVoice}
            onFormatChange={setFormat}
            onVerboseModeChange={setVerboseMode}
            onOutputPathChange={setOutputPath}
          />

          {/* Conversion Button */}
          <div className="flex justify-center">
            <Button
              onClick={handleStartConversion}
              disabled={!canConvert}
              size="lg"
              className="px-8 py-6 text-lg font-semibold shadow-lg hover:shadow-xl transition-all duration-200"
            >
              <Mic className="size-5 mr-2" />
              {isConverting ? "Converting..." : "Convert to Speech"}
            </Button>
          </div>

          {/* Progress */}
          <ConversionProgress
            isConverting={isConverting}
            progress={progress}
            message={progressMessage}
            error={error}
          />

          {/* Results */}
          {result && (
            <AudioResult
              audioPath={result.audioPath}
              fileName={result.fileName}
              fileSize={result.fileSize}
              processingTime={result.processingTime}
              voiceUsed={result.voiceUsed}
              onPlayAudio={handlePlayAudio}
              onOpenFile={handleOpenFile}
              onOpenFolder={handleOpenFolder}
              onConvertAnother={handleConvertAnother}
            />
          )}
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t bg-muted/30 mt-16">
        <div className="container mx-auto px-6 py-4">
          <div className="flex items-center justify-between text-sm text-muted-foreground">
            <div>
              Powered by <span className="font-medium">Google Cloud TTS</span>
            </div>
            <div className="flex items-center gap-4">
              <span>v1.0.0</span>
              <span>•</span>
              <span className="text-green-600 font-medium">Ready</span>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}

export default App;
