import { useState } from 'react';
import { Play, Pause, Download, FolderOpen, RotateCcw } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

interface AudioResultProps {
  audioPath: string;
  fileName: string;
  fileSize: string;
  processingTime: string;
  voiceUsed: string;
  onPlayAudio: () => void;
  onOpenFile: () => void;
  onOpenFolder: () => void;
  onConvertAnother: () => void;
}

export function AudioResult({
  audioPath,
  fileName,
  fileSize,
  processingTime,
  voiceUsed,
  onPlayAudio,
  onOpenFile,
  onOpenFolder,
  onConvertAnother,
}: AudioResultProps) {
  const [isPlaying, setIsPlaying] = useState(false);

  const handlePlayClick = () => {
    setIsPlaying(!isPlaying);
    onPlayAudio();
  };

  return (
    <Card className="animate-in slide-in-from-bottom-2 duration-500">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-green-600 dark:text-green-400">
              Conversion Successful! 🎉
            </CardTitle>
            <CardDescription>
              Your audio file is ready to use
            </CardDescription>
          </div>
          <Badge variant="outline" className="text-green-600 border-green-200">
            Complete
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* File Info */}
        <div className="rounded-lg bg-muted/50 p-4">
          <div className="flex items-center justify-between">
            <div className="flex-1 min-w-0">
              <p className="font-medium truncate">{fileName}</p>
              <p className="text-xs text-muted-foreground truncate" title={audioPath}>
                Saved to: {audioPath}
              </p>
              <p className="text-sm text-muted-foreground">{fileSize}</p>
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handlePlayClick}
                className="flex items-center gap-2"
              >
                {isPlaying ? (
                  <Pause className="size-4" />
                ) : (
                  <Play className="size-4" />
                )}
                {isPlaying ? 'Pause' : 'Play'}
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={onOpenFile}
                className="flex items-center gap-2"
              >
                <Download className="size-4" />
                Open
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={onOpenFolder}
                className="flex items-center gap-2"
              >
                <FolderOpen className="size-4" />
                Folder
              </Button>
            </div>
          </div>
        </div>

        {/* Stats */}
        <div className="grid gap-4 md:grid-cols-2">
          <div className="rounded-lg bg-muted/50 p-3 text-center">
            <div className="text-sm text-muted-foreground mb-1">Processing Time</div>
            <div className="text-lg font-semibold">{processingTime}</div>
          </div>
          <div className="rounded-lg bg-muted/50 p-3 text-center">
            <div className="text-sm text-muted-foreground mb-1">Voice Used</div>
            <div className="text-lg font-semibold truncate">{voiceUsed}</div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex justify-center">
          <Button
            onClick={onConvertAnother}
            className="flex items-center gap-2"
            size="lg"
          >
            <RotateCcw className="size-4" />
            Convert Another File
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}