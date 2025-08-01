import { CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';

interface ConversionProgressProps {
  isConverting: boolean;
  progress: number;
  message: string;
  error?: string;
}

export function ConversionProgress({
  isConverting,
  progress,
  message,
  error,
}: ConversionProgressProps) {
  if (!isConverting && !error && progress === 0) {
    return null;
  }

  return (
    <Card className="animate-in slide-in-from-top-2 duration-300">
      <CardHeader>
        <div className="flex items-center gap-2">
          {error ? (
            <AlertCircle className="size-5 text-destructive" />
          ) : isConverting ? (
            <Loader2 className="size-5 animate-spin text-primary" />
          ) : (
            <CheckCircle className="size-5 text-green-500" />
          )}
          <CardTitle>
            {error ? 'Conversion Failed' : isConverting ? 'Converting...' : 'Conversion Complete'}
          </CardTitle>
        </div>
        <CardDescription>
          {error ? 'An error occurred during conversion' : message}
        </CardDescription>
      </CardHeader>
      <CardContent>
        {!error && (
          <div className="space-y-4">
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span>Progress</span>
                <Badge variant="outline">{Math.round(progress)}%</Badge>
              </div>
              <Progress value={progress} className="h-2" />
            </div>
            
            {!isConverting && progress === 100 && (
              <div className="rounded-lg bg-green-50 dark:bg-green-950/20 p-4 border border-green-200 dark:border-green-800">
                <div className="flex items-center gap-2 text-green-700 dark:text-green-400">
                  <CheckCircle className="size-4" />
                  <span className="text-sm font-medium">Conversion completed successfully!</span>
                </div>
              </div>
            )}
          </div>
        )}
        
        {error && (
          <div className="rounded-lg bg-destructive/10 p-4 border border-destructive/20">
            <div className="flex items-center gap-2 text-destructive">
              <AlertCircle className="size-4" />
              <span className="text-sm font-medium">{error}</span>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}