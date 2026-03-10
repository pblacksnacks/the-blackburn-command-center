import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Building2, FileText, Radar, GitBranch } from 'lucide-react';
import { useMode } from '../modeContext';

const nav = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/research', label: 'Research', icon: Building2 },
  { to: '/briefings', label: 'Briefings', icon: FileText },
];

export default function Layout({ children, onPipelineComplete }: { children: React.ReactNode; onPipelineComplete?: () => void }) {
  const { pathname } = useLocation();
  const mode = useMode();
  const LogoIcon = mode === 'gitlab' ? GitBranch : Radar;

  return (
    <div className="min-h-screen" style={{ background: 'var(--bg-base)' }}>
      <header
        className="px-6 py-3 flex items-center justify-between border-b"
        style={{ background: 'var(--bg-card-solid)', borderColor: 'var(--border)' }}
      >
        <div className="flex items-center gap-6">
          <Link to="/" className="flex items-center gap-2.5 font-bold text-lg tracking-tight" style={{ color: 'var(--text-primary)' }}>
            <div
              className="flex items-center justify-center w-8 h-8 rounded-lg shadow-lg"
              style={{ background: 'var(--accent)', boxShadow: '0 4px 12px color-mix(in srgb, var(--accent) 30%, transparent)' }}
            >
              <LogoIcon className="h-4 w-4 text-white" />
            </div>
            <div className="flex flex-col">
              <span>Blackburn Command Center</span>
              <span className="text-[10px] font-medium tracking-wide uppercase" style={{ color: 'var(--text-muted)' }}>
                {mode === 'gitlab' ? 'GitLab Edition' : 'Anthropic Edition'}
              </span>
            </div>
          </Link>
          <nav className="flex gap-1">
            {nav.map(({ to, label, icon: Icon }) => (
              <Link
                key={to}
                to={to}
                className="inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors"
                style={
                  pathname === to
                    ? { background: 'color-mix(in srgb, var(--accent) 15%, transparent)', color: 'var(--accent)' }
                    : { color: 'var(--text-muted)' }
                }
                onMouseEnter={(e) => {
                  if (pathname !== to) {
                    e.currentTarget.style.color = 'var(--text-primary)';
                    e.currentTarget.style.background = 'var(--border-hover)';
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
      </header>

      <main className="p-6">{children}</main>
    </div>
  );
}
