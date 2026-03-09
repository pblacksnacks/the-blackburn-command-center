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
          className="inline-flex items-center gap-1 rounded-lg bg-white/10 border border-white/10 px-3 py-1.5 text-xs font-medium text-slate-200 hover:bg-white/20 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
        >
          <Play className="h-3 w-3" />
          {s}
        </button>
      ))}

      {job?.status === 'running' && (
        <span className="inline-flex items-center gap-1.5 text-xs text-blue-300 font-medium">
          <Loader2 className="h-3.5 w-3.5 animate-spin" /> Running {job.stage}...
        </span>
      )}
      {job?.status === 'completed' && (
        <span className="inline-flex items-center gap-1.5 text-xs text-emerald-400 font-medium">
          <CheckCircle className="h-3.5 w-3.5" /> Done
        </span>
      )}
      {job?.status === 'failed' && (
        <span className="inline-flex items-center gap-1.5 text-xs text-red-400 font-medium">
          <XCircle className="h-3.5 w-3.5" /> {job.error}
        </span>
      )}
      {error && <span className="text-xs text-red-400 font-medium">{error}</span>}
    </div>
  );
}
