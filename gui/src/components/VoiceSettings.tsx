import { useState, useEffect } from 'react';
import { Settings, RefreshCw, Volume2, FolderOpen } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { Button } from '@/components/ui/button';
import { Checkbox } from '@/components/ui/checkbox';
import { Badge } from '@/components/ui/badge';
import { invoke } from '@tauri-apps/api/core';

interface Voice {
  name: string;
  language_code: string;
  ssml_gender: string;
  display_name?: string;
}

interface VoiceSettingsProps {
  language: string;
  voice: string;
  format: string;
  verboseMode: boolean;
  outputPath?: string;
  onLanguageChange: (language: string) => void;
  onVoiceChange: (voice: string) => void;
  onFormatChange: (format: string) => void;
  onVerboseModeChange: (verbose: boolean) => void;
  onOutputPathChange?: (path: string) => void;
}

const languages = [
  { code: 'en-US', name: 'English (US)', flag: '🇺🇸' },
  { code: 'en-GB', name: 'English (UK)', flag: '🇬🇧' },
  { code: 'es-ES', name: 'Spanish (Spain)', flag: '🇪🇸' },
  { code: 'fr-FR', name: 'French (France)', flag: '🇫🇷' },
  { code: 'de-DE', name: 'German (Germany)', flag: '🇩🇪' },
  { code: 'it-IT', name: 'Italian (Italy)', flag: '🇮🇹' },
  { code: 'ja-JP', name: 'Japanese (Japan)', flag: '🇯🇵' },
  { code: 'ko-KR', name: 'Korean (South Korea)', flag: '🇰🇷' },
];

const formats = [
  { value: 'MP3', name: 'MP3 Audio', description: 'Compressed, smaller file size' },
  { value: 'WAV', name: 'WAV Audio', description: 'Uncompressed, higher quality' },
];

export function VoiceSettings({
  language,
  voice,
  format,
  verboseMode,
  outputPath,
  onLanguageChange,
  onVoiceChange,
  onFormatChange,
  onVerboseModeChange,
  onOutputPathChange,
}: VoiceSettingsProps) {
  const [voices, setVoices] = useState<Voice[]>([]);
  const [isLoadingVoices, setIsLoadingVoices] = useState(false);

  const handleSelectOutputFolder = async () => {
    try {
      const selectedPath = await invoke<string | null>('select_output_folder');
      if (selectedPath && onOutputPathChange) {
        onOutputPathChange(selectedPath);
      }
    } catch (error) {
      console.error('Failed to select output folder:', error);
    }
  };

  const loadVoices = async () => {
    setIsLoadingVoices(true);
    try {
      // Call Tauri command to get voices
      const voiceList = await invoke<Voice[]>('get_available_voices', { 
        languageCode: language 
      });
      
      setVoices(voiceList);
      if (!voice && voiceList.length > 0) {
        onVoiceChange(voiceList[0].name);
      }
    } catch (error) {
      console.error('Failed to load voices:', error);
      
      // Fallback to mock voices if service is unavailable
      const mockVoices: Voice[] = [
        { name: 'neural-female-1', language_code: language, ssml_gender: 'FEMALE', display_name: 'Sarah (Neural)' },
        { name: 'neural-male-1', language_code: language, ssml_gender: 'MALE', display_name: 'David (Neural)' },
        { name: 'standard-female-1', language_code: language, ssml_gender: 'FEMALE', display_name: 'Emma (Standard)' },
        { name: 'standard-male-1', language_code: language, ssml_gender: 'MALE', display_name: 'James (Standard)' },
      ];
      
      setVoices(mockVoices);
      if (!voice && mockVoices.length > 0) {
        onVoiceChange(mockVoices[0].name);
      }
    } finally {
      setIsLoadingVoices(false);
    }
  };

  useEffect(() => {
    loadVoices();
  }, [language]);

  const selectedLanguage = languages.find(lang => lang.code === language);
  const selectedVoice = voices.find(v => v.name === voice);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <Settings className="size-5" />
          <CardTitle>Voice & Settings</CardTitle>
        </div>
        <CardDescription>
          Configure your text-to-speech preferences
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <div className="grid gap-6 md:grid-cols-2">
          {/* Language Selection */}
          <div className="space-y-2">
            <Label>Language</Label>
            <Select value={language} onValueChange={onLanguageChange}>
              <SelectTrigger>
                <SelectValue>
                  {selectedLanguage && (
                    <div className="flex items-center gap-2">
                      <span>{selectedLanguage.flag}</span>
                      <span>{selectedLanguage.name}</span>
                    </div>
                  )}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {languages.map((lang) => (
                  <SelectItem key={lang.code} value={lang.code}>
                    <div className="flex items-center gap-2">
                      <span>{lang.flag}</span>
                      <span>{lang.name}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Voice Selection */}
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Label>Voice</Label>
              <Button
                variant="ghost"
                size="sm"
                onClick={loadVoices}
                disabled={isLoadingVoices}
                className="h-6 px-2"
              >
                <RefreshCw className={`size-3 ${isLoadingVoices ? 'animate-spin' : ''}`} />
              </Button>
            </div>
            <Select value={voice} onValueChange={onVoiceChange} disabled={isLoadingVoices}>
              <SelectTrigger>
                <SelectValue>
                  {selectedVoice ? (
                    <div className="flex items-center gap-2">
                      <Volume2 className="size-4" />
                      <span>{selectedVoice.display_name || selectedVoice.name}</span>
                      <Badge variant="outline" className="text-xs">
                        {selectedVoice.ssml_gender === 'FEMALE' ? 'F' : 'M'}
                      </Badge>
                    </div>
                  ) : (
                    'Select voice...'
                  )}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                {voices.map((voice) => (
                  <SelectItem key={voice.name} value={voice.name}>
                    <div className="flex items-center gap-2">
                      <Volume2 className="size-4" />
                      <span>{voice.display_name || voice.name}</span>
                      <Badge variant="outline" className="text-xs">
                        {voice.ssml_gender === 'FEMALE' ? 'F' : 'M'}
                      </Badge>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        {/* Format Selection */}
        <div className="space-y-2">
          <Label>Output Format</Label>
          <Select value={format} onValueChange={onFormatChange}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {formats.map((fmt) => (
                <SelectItem key={fmt.value} value={fmt.value}>
                  <div>
                    <div className="font-medium">{fmt.name}</div>
                    <div className="text-xs text-muted-foreground">{fmt.description}</div>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Output Path */}
        <div className="space-y-2">
          <Label>Output Location</Label>
          <div className="flex items-center gap-2">
            <div className="flex-1 px-3 py-2 text-sm border rounded-md bg-muted/50 text-muted-foreground">
              {outputPath ? (
                <span className="truncate">{outputPath}</span>
              ) : (
                <span>Default location (Downloads)</span>
              )}
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={handleSelectOutputFolder}
              className="shrink-0"
            >
              <FolderOpen className="size-4 mr-2" />
              Browse
            </Button>
          </div>
          <p className="text-xs text-muted-foreground">
            Choose where to save generated audio files
          </p>
        </div>

        {/* Options */}
        <div className="space-y-4">
          <div className="flex items-center space-x-3">
            <Checkbox
              id="verbose"
              checked={verboseMode}
              onCheckedChange={onVerboseModeChange}
            />
            <div className="grid gap-1.5 leading-none">
              <Label htmlFor="verbose" className="text-sm font-medium leading-none">
                Verbose Output
              </Label>
              <p className="text-xs text-muted-foreground">
                Show detailed processing information
              </p>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}