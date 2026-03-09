import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Building2, FileText, Radar } from 'lucide-react';
// PipelineRunner hidden during demo — costs API credits
// import PipelineRunner from './PipelineRunner';

const nav = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/research', label: 'Research', icon: Building2 },
  { to: '/briefings', label: 'Briefings', icon: FileText },
];

export default function Layout({ children, onPipelineComplete }: { children: React.ReactNode; onPipelineComplete?: () => void }) {
  const { pathname } = useLocation();

  return (
    <div className="min-h-screen" style={{ background: 'var(--bg-base)' }}>
      <header
        className="px-6 py-3 flex items-center justify-between border-b"
        style={{ background: 'rgba(18, 17, 16, 0.95)', borderColor: 'var(--border)' }}
      >
        <div className="flex items-center gap-6">
          <Link to="/" className="flex items-center gap-2.5 font-bold text-lg tracking-tight" style={{ color: 'var(--text-primary)' }}>
            <div
              className="flex items-center justify-center w-8 h-8 rounded-lg shadow-lg"
              style={{ background: 'var(--accent)', boxShadow: '0 4px 12px rgba(212, 165, 116, 0.3)' }}
            >
              <Radar className="h-4 w-4 text-white" />
            </div>
            Blackburn Command Center
          </Link>
          <nav className="flex gap-1">
            {nav.map(({ to, label, icon: Icon }) => (
              <Link
                key={to}
                to={to}
                className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors"
                style={
                  pathname === to
                    ? { background: 'rgba(212, 165, 116, 0.15)', color: 'var(--accent)' }
                    : { color: 'var(--text-muted)' }
                }
                onMouseEnter={(e) => {
                  if (pathname !== to) {
                    e.currentTarget.style.color = 'var(--text-primary)';
                    e.currentTarget.style.background = 'rgba(245, 240, 232, 0.05)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (pathname !== to) {
                    e.currentTarget.style.color = 'var(--text-muted)';
                    e.currentTarget.style.background = 'transparent';
                  }
                }}
              >
                <Icon className="h-4 w-4" />
                {label}
              </Link>
            ))}
          </nav>
        </div>
        {/* PipelineRunner hidden during demo */}
      </header>

      <main className="p-6">{children}</main>
    </div>
  );
}
