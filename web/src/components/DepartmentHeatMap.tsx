/* ── Department config ─────────────────────────────────────────── */

const deptConfig = [
  { key: 'Engineering', fraction: 0.30 },
  { key: 'Sales', fraction: 0.15 },
  { key: 'Marketing', fraction: 0.08 },
  { key: 'Product', fraction: 0.10 },
  { key: 'Legal', fraction: 0.03 },
  { key: 'Support', fraction: 0.12 },
  { key: 'HR', fraction: 0.04 },
  { key: 'Finance', fraction: 0.05 },
] as const;

const products = [
  { key: 'Claude API', price: 3600 },
  { key: 'Claude.ai', price: 720 },
  { key: 'Claude Code', price: 1440 },
  { key: 'Claude Enterprise', price: 1440 },
] as const;

/* Adoption rate: fraction of dept employees expected to use each product */
const fitMatrix: Record<string, Record<string, number>> = {
  'Claude API': {
    Engineering: 0.70, Sales: 0.05, Marketing: 0.05, Product: 0.50,
    Legal: 0.02, Support: 0.15, HR: 0.02, Finance: 0.02,
  },
  'Claude.ai': {
    Engineering: 0.40, Sales: 0.80, Marketing: 0.85, Product: 0.50,
    Legal: 0.70, Support: 0.60, HR: 0.75, Finance: 0.60,
  },
  'Claude Code': {
    Engineering: 0.85, Sales: 0.0, Marketing: 0.0, Product: 0.35,
    Legal: 0.0, Support: 0.05, HR: 0.0, Finance: 0.0,
  },
  'Claude Enterprise': {
    Engineering: 0.15, Sales: 0.20, Marketing: 0.15, Product: 0.15,
    Legal: 0.10, Support: 0.10, HR: 0.10, Finance: 0.10,
  },
};

/* ── Computation ──────────────────────────────────────────────── */

interface Cell {
  product: string;
  dept: string;
  seats: number;
  value: number;
}

function computeGrid(totalEmployees: number) {
  const cells: Cell[] = [];
  let maxValue = 0;

  for (const product of products) {
    for (const dept of deptConfig) {
      const deptEmployees = Math.round(totalEmployees * dept.fraction);
      const adoptionRate = fitMatrix[product.key]?.[dept.key] ?? 0;
      const seats = Math.round(deptEmployees * adoptionRate);
      const value = seats * product.price;
      cells.push({ product: product.key, dept: dept.key, seats, value });
      if (value > maxValue) maxValue = value;
    }
  }

  return { cells, maxValue };
}

function intensityStyle(value: number, maxValue: number): React.CSSProperties {
  if (maxValue === 0 || value === 0) return { background: 'rgba(245, 240, 232, 0.03)', color: 'var(--text-muted)' };
  const ratio = value / maxValue;
  if (ratio >= 0.6) return { background: 'rgba(16, 185, 129, 0.3)', color: '#6ee7b7' };
  if (ratio >= 0.3) return { background: 'rgba(16, 185, 129, 0.18)', color: '#6ee7b7' };
  if (ratio >= 0.1) return { background: 'rgba(16, 185, 129, 0.08)', color: '#a7f3d0' };
  return { background: 'rgba(16, 185, 129, 0.04)', color: 'var(--text-muted)' };
}

function formatValue(v: number): string {
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `$${(v / 1_000).toFixed(0)}K`;
  return `$${v}`;
}

/* ── Component ────────────────────────────────────────────────── */

export default function DepartmentHeatMap({
  employeeEstimate,
  companyName,
}: {
  employeeEstimate: number;
  companyName: string | null;
}) {
  const { cells, maxValue } = computeGrid(employeeEstimate);

  const getCell = (product: string, dept: string) =>
    cells.find((c) => c.product === product && c.dept === dept)!;

  // Column totals
  const deptTotals = deptConfig.map((dept) => {
    const totalValue = products.reduce((sum, p) => sum + getCell(p.key, dept.key).value, 0);
    const totalSeats = products.reduce((sum, p) => sum + getCell(p.key, dept.key).seats, 0);
    return { dept: dept.key, value: totalValue, seats: totalSeats };
  });

  const grandTotal = deptTotals.reduce((sum, d) => sum + d.value, 0);
  const grandSeats = deptTotals.reduce((sum, d) => sum + d.seats, 0);

  return (
    <div
      className="rounded-xl p-5 mb-4 animate-fade-in-up"
      style={{ background: 'var(--bg-card)', border: '1px solid var(--border)' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-sm font-semibold flex items-center gap-2" style={{ color: 'var(--text-secondary)' }}>
          <svg
            className="h-4 w-4"
            style={{ color: 'var(--text-muted)' }}
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M3.75 3v11.25A2.25 2.25 0 006 16.5h2.25M3.75 3h-1.5m1.5 0h16.5m0 0h1.5m-1.5 0v11.25A2.25 2.25 0 0118 16.5h-2.25m-7.5 0h7.5m-7.5 0l-1 3m8.5-3l1 3m0 0l.5 1.5m-.5-1.5h-9.5m0 0l-.5 1.5"
            />
          </svg>
          Department Revenue Heat Map
          {companyName && (
            <span style={{ color: 'var(--text-muted)' }} className="font-normal"> &mdash; {companyName}</span>
          )}
        </h2>
        <div className="flex items-center gap-4 text-xs" style={{ color: 'var(--text-muted)' }}>
          <span>~{employeeEstimate.toLocaleString()} employees</span>
          <span className="font-bold text-sm" style={{ color: 'var(--text-primary)' }}>
            TAM: {formatValue(grandTotal)}
          </span>
        </div>
      </div>

      {/* Grid */}
      <div className="overflow-x-auto">
        <table className="w-full min-w-[740px] text-xs border-separate border-spacing-1">
          <thead>
            <tr>
              <th className="text-left py-2 px-2 text-[10px] font-bold uppercase tracking-wider w-36" style={{ color: 'var(--text-muted)' }}>
                Product
              </th>
              {deptConfig.map((d) => (
                <th
                  key={d.key}
                  className="text-center py-2 px-1 text-[10px] font-bold uppercase tracking-wider"
                  style={{ color: 'var(--text-muted)' }}
                >
                  {d.key}
                </th>
              ))}
            </tr>
          </thead>

          <tbody>
            {products.map((product) => (
              <tr key={product.key}>
                <td className="py-1 px-2 font-semibold whitespace-nowrap" style={{ color: 'var(--text-secondary)' }}>
                  {product.key}
                </td>
                {deptConfig.map((dept) => {
                  const cell = getCell(product.key, dept.key);
                  return (
                    <td key={dept.key} className="p-0.5">
                      <div
                        className="rounded-lg p-2 text-center transition-colors"
                        style={intensityStyle(cell.value, maxValue)}
                      >
                        <div className="font-bold tabular-nums">
                          {cell.seats > 0 ? cell.seats : '\u2014'}
                        </div>
                        <div className="text-[10px] opacity-80">
                          {cell.value > 0 ? formatValue(cell.value) : '\u2014'}
                        </div>
                      </div>
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>

          <tfoot>
            <tr>
              <td className="py-1 px-2 font-bold" style={{ color: 'var(--text-primary)' }}>Total</td>
              {deptTotals.map((dt) => (
                <td key={dt.dept} className="p-0.5">
                  <div
                    className="rounded-lg p-2 text-center"
                    style={{ background: 'rgba(245, 240, 232, 0.08)', color: 'var(--text-primary)' }}
                  >
                    <div className="font-bold tabular-nums">{dt.seats}</div>
                    <div className="text-[10px]" style={{ color: 'var(--text-muted)' }}>{formatValue(dt.value)}</div>
                  </div>
                </td>
              ))}
            </tr>

            {/* Grand total row */}
            <tr>
              <td colSpan={deptConfig.length + 1} className="pt-3 px-2">
                <div
                  className="flex items-center justify-between rounded-lg px-4 py-3"
                  style={{
                    background: 'linear-gradient(to right, rgba(212, 165, 116, 0.12), rgba(212, 165, 116, 0.06))',
                    border: '1px solid rgba(212, 165, 116, 0.2)',
                  }}
                >
                  <div>
                    <div className="text-[10px] font-medium uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
                      Full Account TAM
                    </div>
                    <div className="text-xl font-extrabold tracking-tight" style={{ color: 'var(--accent)' }}>
                      {formatValue(grandTotal)}
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-[10px] font-medium uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>
                      Total Seats
                    </div>
                    <div className="text-xl font-extrabold tracking-tight tabular-nums" style={{ color: 'var(--text-primary)' }}>
                      {grandSeats.toLocaleString()}
                    </div>
                  </div>
                </div>
              </td>
            </tr>
          </tfoot>
        </table>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-5 mt-4 pt-3 text-[10px]" style={{ borderTop: '1px solid var(--border)', color: 'var(--text-muted)' }}>
        <span className="font-semibold" style={{ color: 'var(--text-secondary)' }}>Intensity:</span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded" style={{ background: 'rgba(16, 185, 129, 0.3)' }} /> High
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded" style={{ background: 'rgba(16, 185, 129, 0.18)' }} /> Medium
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded" style={{ background: 'rgba(16, 185, 129, 0.08)' }} /> Low
        </span>
        <span className="flex items-center gap-1">
          <span className="w-3 h-3 rounded" style={{ background: 'rgba(16, 185, 129, 0.04)', border: '1px solid rgba(16, 185, 129, 0.1)' }} /> Minimal
        </span>
        <span className="ml-auto" style={{ color: 'var(--text-muted)' }}>
          Seats = dept headcount &times; product adoption rate &bull; Values = seats &times;
          annual price
        </span>
      </div>
    </div>
  );
}
