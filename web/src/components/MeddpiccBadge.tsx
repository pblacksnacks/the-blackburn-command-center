import { useState, useRef, useEffect } from 'react';
import type { MeddpiccDimension } from '../api';

/* ── status → visual mapping ─────────────────────────────────── */

const badgeColors: Record<string, string> = {
  known: 'bg-emerald-900/40 text-emerald-300 border-emerald-700/50',
  partial: 'bg-amber-900/30 text-amber-300 border-amber-700/40',
  unknown: 'bg-white/5 text-[var(--text-muted)] border-[var(--border)]',
};

const dotColors: Record<string, string> = {
  known: 'bg-emerald-500',
  partial: 'bg-amber-500',
  unknown: 'bg-gray-500',
};

const expandBorderColors: Record<string, string> = {
  known: 'border-emerald-800/40',
  partial: 'border-amber-800/40',
  unknown: 'border-[var(--border)]',
};

const expandAccent: Record<string, string> = {
  known: 'bg-emerald-900/20',
  partial: 'bg-amber-900/20',
  unknown: 'bg-white/3',
};

/* ── labels ──────────────────────────────────────────────────── */

const labels: Record<string, string> = {
  metrics: 'Metrics',
  economic_buyer: 'Econ. Buyer',
  decision_criteria: 'Decision Criteria',
  decision_process: 'Decision Process',
  paper_process: 'Paper Process',
  implicate_pain: 'Implicate Pain',
  champion: 'Champion',
  competition: 'Competition',
};

const letterMap: Record<string, string> = {
  metrics: 'M',
  economic_buyer: 'E',
  decision_criteria: 'D',
  decision_process: 'D',
  paper_process: 'P',
  implicate_pain: 'I',
  champion: 'C',
  competition: 'C',
};

/* ── helpers ─────────────────────────────────────────────────── */

function normalize(value: string | MeddpiccDimension): MeddpiccDimension {
  if (typeof value === 'string') {
    return { status: value as MeddpiccDimension['status'], evidence: '', gap: '', question: '' };
  }
  return value;
}

function hoverPreview(dim: MeddpiccDimension): string {
  if (dim.status === 'known' && dim.evidence) return dim.evidence;
  if (dim.status === 'partial' && dim.evidence) return dim.evidence;
  if (dim.gap) return dim.gap;
  if (dim.status === 'unknown') return 'No intel yet — click to see what to ask';
  return 'Click to expand';
}

/* ── DimensionBadge ──────────────────────────────────────────── */

function DimensionBadge({
  dimensionKey,
  dimension,
  isExpanded,
  onToggle,
}: {
  dimensionKey: string;
  dimension: MeddpiccDimension;
  isExpanded: boolean;
  onToggle: () => void;
}) {
  const [hovered, setHovered] = useState(false);
  const hoverTimer = useRef<ReturnType<typeof setTimeout>>();
  const tooltipRef = useRef<HTMLDivElement>(null);
  const badgeRef = useRef<HTMLDivElement>(null);
  const [tooltipSide, setTooltipSide] = useState<'top' | 'bottom'>('top');

  const status = dimension.status || 'unknown';
  const preview = hoverPreview(dimension);

  useEffect(() => {
    if (hovered && badgeRef.current) {
      const rect = badgeRef.current.getBoundingClientRect();
      setTooltipSide(rect.top < 120 ? 'bottom' : 'top');
    }
  }, [hovered]);

  const showHover = () => {
    clearTimeout(hoverTimer.current);
    hoverTimer.current = setTimeout(() => setHovered(true), 200);
  };
  const hideHover = () => {
    clearTimeout(hoverTimer.current);
    hoverTimer.current = setTimeout(() => setHovered(false), 150);
  };

  return (
    <div className="relative" ref={badgeRef}>
      <button
        type="button"
        onClick={onToggle}
        onMouseEnter={showHover}
        onMouseLeave={hideHover}
        className={`
          w-full rounded border px-2.5 py-1.5 text-xs font-semibold cursor-pointer
          transition-all duration-150 select-none
          ${badgeColors[status]}
          ${isExpanded ? 'ring-2 ring-[var(--accent)] ring-offset-1 ring-offset-[var(--bg-card-solid)]' : 'hover:shadow-md'}
        `}
      >
        <div className="flex items-center justify-between gap-1.5">
          <div className="flex items-center gap-1.5">
            <span className={`inline-flex items-center justify-center w-4 h-4 rounded text-[9px] font-bold text-white ${dotColors[status]}`}>
              {letterMap[dimensionKey]}
            </span>
            <span>{labels[dimensionKey]}</span>
          </div>
          <svg
            className={`w-3 h-3 text-current opacity-60 transition-transform duration-150 ${isExpanded ? 'rotate-180' : ''}`}
            fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
          </svg>
        </div>
      </button>

      {hovered && !isExpanded && (
        <div
          ref={tooltipRef}
          onMouseEnter={showHover}
          onMouseLeave={hideHover}
          className="absolute z-50 w-64 rounded-lg shadow-lg px-3 py-2 text-xs leading-relaxed pointer-events-auto"
          style={{
            background: 'var(--bg-elevated)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border)',
            ...(tooltipSide === 'top'
              ? { bottom: '100%', left: '50%', transform: 'translateX(-50%)', marginBottom: 6 }
              : { top: '100%', left: '50%', transform: 'translateX(-50%)', marginTop: 6 }),
          }}
        >
          <p className="line-clamp-3">{preview}</p>
          <div
            className="absolute w-2 h-2 rotate-45"
            style={{
              background: 'var(--bg-elevated)',
              ...(tooltipSide === 'top'
                ? { bottom: -4, left: '50%', transform: 'translateX(-50%) rotate(45deg)' }
                : { top: -4, left: '50%', transform: 'translateX(-50%) rotate(45deg)' }),
            }}
          />
        </div>
      )}
    </div>
  );
}

/* ── Expanded detail panel ───────────────────────────────────── */

function ExpandedDetail({
  dimensionKey,
  dimension,
  onClose,
}: {
  dimensionKey: string;
  dimension: MeddpiccDimension;
  onClose: () => void;
}) {
  const status = dimension.status || 'unknown';
  const hasEvidence = Boolean(dimension.evidence);
  const hasGap = Boolean(dimension.gap);
  const hasQuestion = Boolean(dimension.question);

  return (
    <div
      className={`col-span-2 rounded-lg border p-4 animate-in fade-in duration-150 ${expandBorderColors[status]} ${expandAccent[status]}`}
    >
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={`inline-flex items-center justify-center w-5 h-5 rounded text-[10px] font-bold text-white ${dotColors[status]}`}>
            {letterMap[dimensionKey]}
          </span>
          <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{labels[dimensionKey]}</span>
          <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${badgeColors[status]}`}>
            {status === 'known' ? 'Confirmed' : status === 'partial' ? 'Partial Intel' : 'No Intel'}
          </span>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="transition-colors p-0.5"
          style={{ color: 'var(--text-muted)' }}
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div className="space-y-3">
        {hasEvidence && (
          <div className="rounded border border-emerald-800/30 p-3" style={{ background: 'rgba(16, 185, 129, 0.08)' }}>
            <div className="flex items-center gap-1.5 mb-1">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              <span className="text-[10px] font-semibold uppercase tracking-wide text-emerald-400">What We Know</span>
            </div>
            <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{dimension.evidence}</p>
          </div>
        )}

        {hasGap && (
          <div className="rounded border border-amber-800/30 p-3" style={{ background: 'rgba(245, 158, 11, 0.08)' }}>
            <div className="flex items-center gap-1.5 mb-1">
              <div className="w-1.5 h-1.5 rounded-full bg-amber-500" />
              <span className="text-[10px] font-semibold uppercase tracking-wide text-amber-400">Gap to Close</span>
            </div>
            <p className="text-sm leading-relaxed" style={{ color: 'var(--text-secondary)' }}>{dimension.gap}</p>
          </div>
        )}

        {hasQuestion && (
          <div className="rounded border p-3" style={{ background: 'color-mix(in srgb, var(--accent) 6%, transparent)', borderColor: 'color-mix(in srgb, var(--accent) 20%, transparent)' }}>
            <div className="flex items-center gap-1.5 mb-1">
              <div className="w-1.5 h-1.5 rounded-full" style={{ background: 'var(--accent)' }} />
              <span className="text-[10px] font-semibold uppercase tracking-wide" style={{ color: 'var(--accent)' }}>Discovery Question</span>
            </div>
            <p className="text-sm leading-relaxed italic" style={{ color: 'var(--text-secondary)' }}>
              &ldquo;{dimension.question}&rdquo;
            </p>
          </div>
        )}

        {!hasEvidence && !hasGap && !hasQuestion && (
          <p className="text-sm italic" style={{ color: 'var(--text-muted)' }}>
            No enriched detail available. Re-run the pipeline to generate per-dimension intel.
          </p>
        )}
      </div>
    </div>
  );
}

/* ── Main component ──────────────────────────────────────────── */

export default function MeddpiccBadge({
  meddpicc,
}: {
  meddpicc: Record<string, string | MeddpiccDimension>;
}) {
  const [expandedKey, setExpandedKey] = useState<string | null>(null);
  const keys = Object.keys(labels);

  const rows: string[][] = [];
  for (let i = 0; i < keys.length; i += 2) {
    rows.push(keys.slice(i, i + 2));
  }

  return (
    <div className="space-y-2">
      {rows.map((row) => {
        const expandedInRow = row.find((k) => k === expandedKey);
        return (
          <div key={row.join('-')}>
            <div className="grid grid-cols-2 gap-2">
              {row.map((key) => {
                const raw = meddpicc[key] || 'unknown';
                const dim = normalize(raw);
                return (
                  <DimensionBadge
                    key={key}
                    dimensionKey={key}
                    dimension={dim}
                    isExpanded={expandedKey === key}
                    onToggle={() => setExpandedKey(expandedKey === key ? null : key)}
                  />
                );
              })}
            </div>

            {expandedInRow && (
              <div className="grid grid-cols-1 mt-2">
                <ExpandedDetail
                  dimensionKey={expandedInRow}
                  dimension={normalize(meddpicc[expandedInRow] || 'unknown')}
                  onClose={() => setExpandedKey(null)}
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
