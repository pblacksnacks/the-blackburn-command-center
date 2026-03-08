import { useState, useEffect } from 'react';
import { Play, Loader2, CheckCircle, XCircle } from 'lucide-react';
import { runPipeline, fetchPipelineStatus, type PipelineJob } from '../api';

export default function PipelineRunner({ onComplete }: { onComplete?: () => void }) {
  const [job, setJob] = useState<PipelineJob | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!job || job.status !== 'running') return;
    const interval = setInterval(async () => {
      try {
        const updated = await fetchPipelineStatus(job.id);
        setJob(updated);
        if (updated.status !== 'running') {
          clearInterval(interval);
          if (updated.status === 'completed') onComplete?.();
        }
      } catch { /* keep polling */ }
    }, 2000);
    return () => clearInterval(interval);
  }, [job, onComplete]);

  const run = async (stage: string) => {
    setError(null);
    try {
      const j = await runPipeline(stage, true);
      setJob(j);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to start');
    }
  };

  const stages = ['full', 'intake', 'research', 'briefing'] as const;

  return (
    <div className="flex items-center gap-2">
      {stages.map((s) => (
        <button
          key={s}
          onClick={() => run(s)}
          disabled={job?.status === 'running'}
          className="inline-flex items-center gap-1 rounded bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <Play className="h-3 w-3" />
          {s}
        </button>
      ))}

      {job?.status === 'running' && (
        <span className="inline-flex items-center gap-1 text-xs text-blue-600">
          <Loader2 className="h-3 w-3 animate-spin" /> Running {job.stage}...
        </span>
      )}
      {job?.status === 'completed' && (
        <span className="inline-flex items-center gap-1 text-xs text-green-600">
          <CheckCircle className="h-3 w-3" /> Done
        </span>
      )}
      {job?.status === 'failed' && (
        <span className="inline-flex items-center gap-1 text-xs text-red-600">
          <XCircle className="h-3 w-3" /> {job.error}
        </span>
      )}
      {error && <span className="text-xs text-red-600">{error}</span>}
    </div>
  );
}
