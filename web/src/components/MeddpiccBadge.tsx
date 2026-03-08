const statusColors: Record<string, string> = {
  known: 'bg-green-100 text-green-700',
  partial: 'bg-yellow-100 text-yellow-700',
  unknown: 'bg-gray-100 text-gray-500',
};

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

export default function MeddpiccBadge({ meddpicc }: { meddpicc: Record<string, string> }) {
  return (
    <div className="grid grid-cols-2 gap-2">
      {Object.entries(labels).map(([key, label]) => {
        const status = meddpicc[key] || 'unknown';
        return (
          <div key={key} className={`rounded px-2 py-1 text-xs font-medium ${statusColors[status]}`}>
            {label}: {status}
          </div>
        );
      })}
    </div>
  );
}
