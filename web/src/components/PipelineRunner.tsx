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
          className="inline-flex items-center gap-1 rounded-lg px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          style={{
            background: 'rgba(212, 165, 116, 0.1)',
            border: '1px solid rgba(212, 165, 116, 0.2)',
            color: 'var(--accent)',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'rgba(212, 165, 116, 0.2)';
            e.currentTarget.style.color = 'var(--accent-hover)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'rgba(212, 165, 116, 0.1)';
            e.currentTarget.style.color = 'var(--accent)';
          }}
        >
          <Play className="h-3 w-3" />
          {s}
        </button>
      ))}

      {job?.status === 'running' && (
        <span className="inline-flex items-center gap-1.5 text-xs font-medium" style={{ color: 'var(--accent)' }}>
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
