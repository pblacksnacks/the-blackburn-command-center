import { useState, useRef, useEffect } from 'react';
import type { MeddpiccDimension } from '../api';

/* ── status → visual mapping ─────────────────────────────────── */

const badgeColors: Record<string, string> = {
  known: 'bg-green-100 text-green-800 border-green-300',
  partial: 'bg-yellow-100 text-yellow-800 border-yellow-300',
  unknown: 'bg-gray-100 text-gray-500 border-gray-300',
};

const dotColors: Record<string, string> = {
  known: 'bg-green-500',
  partial: 'bg-yellow-500',
  unknown: 'bg-gray-400',
};

const expandBorderColors: Record<string, string> = {
  known: 'border-green-200',
  partial: 'border-yellow-200',
  unknown: 'border-gray-200',
};

const expandAccent: Record<string, string> = {
  known: 'bg-green-50',
  partial: 'bg-yellow-50',
  unknown: 'bg-gray-50',
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

/** Build the hover preview line — the one key fact or gap a rep needs at a glance. */
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

  // Decide whether tooltip goes above or below based on available space
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
      {/* Badge */}
      <button
        type="button"
        onClick={onToggle}
        onMouseEnter={showHover}
        onMouseLeave={hideHover}
        className={`
          w-full rounded border px-2.5 py-1.5 text-xs font-semibold cursor-pointer
          transition-all duration-150 select-none
          ${badgeColors[status]}
          ${isExpanded ? 'ring-2 ring-indigo-400 ring-offset-1' : 'hover:shadow-md'}
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

      {/* Hover tooltip — quick intel preview */}
      {hovered && !isExpanded && (
        <div
          ref={tooltipRef}
          onMouseEnter={showHover}
          onMouseLeave={hideHover}
          className={`
            absolute z-50 w-64 bg-gray-900 text-white rounded-lg shadow-lg px-3 py-2 text-xs leading-relaxed
            pointer-events-auto
          `}
          style={
            tooltipSide === 'top'
              ? { bottom: '100%', left: '50%', transform: 'translateX(-50%)', marginBottom: 6 }
              : { top: '100%', left: '50%', transform: 'translateX(-50%)', marginTop: 6 }
          }
        >
          <p className="line-clamp-3">{preview}</p>
          <div
            className="absolute w-2 h-2 bg-gray-900 rotate-45"
            style={
              tooltipSide === 'top'
                ? { bottom: -4, left: '50%', transform: 'translateX(-50%) rotate(45deg)' }
                : { top: -4, left: '50%', transform: 'translateX(-50%) rotate(45deg)' }
            }
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
    <div className={`col-span-2 rounded-lg border ${expandBorderColors[status]} ${expandAccent[status]} p-4 animate-in fade-in duration-150`}>
      {/* Top row: title + close */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className={`inline-flex items-center justify-center w-5 h-5 rounded text-[10px] font-bold text-white ${dotColors[status]}`}>
            {letterMap[dimensionKey]}
          </span>
          <span className="text-sm font-semibold text-gray-900">{labels[dimensionKey]}</span>
          <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded ${badgeColors[status]}`}>
            {status === 'known' ? 'Confirmed' : status === 'partial' ? 'Partial Intel' : 'No Intel'}
          </span>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="text-gray-400 hover:text-gray-600 transition-colors p-0.5"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Content sections */}
      <div className="space-y-3">
        {/* Evidence: what we know */}
        {hasEvidence && (
          <div className="bg-white rounded border border-green-200 p-3">
            <div className="flex items-center gap-1.5 mb-1">
              <div className="w-1.5 h-1.5 rounded-full bg-green-500" />
              <span className="text-[10px] font-semibold uppercase tracking-wide text-green-700">What We Know</span>
            </div>
            <p className="text-sm text-gray-800 leading-relaxed">{dimension.evidence}</p>
          </div>
        )}

        {/* Gap: what's missing */}
        {hasGap && (
          <div className="bg-white rounded border border-amber-200 p-3">
            <div className="flex items-center gap-1.5 mb-1">
              <div className="w-1.5 h-1.5 rounded-full bg-amber-500" />
              <span className="text-[10px] font-semibold uppercase tracking-wide text-amber-700">Gap to Close</span>
            </div>
            <p className="text-sm text-gray-800 leading-relaxed">{dimension.gap}</p>
          </div>
        )}

        {/* Question: what to ask */}
        {hasQuestion && (
          <div className="bg-white rounded border border-indigo-200 p-3">
            <div className="flex items-center gap-1.5 mb-1">
              <div className="w-1.5 h-1.5 rounded-full bg-indigo-500" />
              <span className="text-[10px] font-semibold uppercase tracking-wide text-indigo-700">Discovery Question</span>
            </div>
            <p className="text-sm text-gray-800 leading-relaxed italic">
              &ldquo;{dimension.question}&rdquo;
            </p>
          </div>
        )}

        {/* Fallback when no enriched data */}
        {!hasEvidence && !hasGap && !hasQuestion && (
          <p className="text-sm text-gray-400 italic">
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

  // Build rows of 2 so we can inject the expanded panel between rows
  const rows: string[][] = [];
  for (let i = 0; i < keys.length; i += 2) {
    rows.push(keys.slice(i, i + 2));
  }

  return (
    <div className="space-y-2">
      {rows.map((row) => {
        // Check if expanded item lives in this row
        const expandedInRow = row.find((k) => k === expandedKey);
        return (
          <div key={row.join('-')}>
            {/* Badge row */}
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

            {/* Expanded detail — slides in below the row it belongs to */}
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
