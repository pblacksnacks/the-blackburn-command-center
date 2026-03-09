import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Building2, FileText, Radar } from 'lucide-react';
import PipelineRunner from './PipelineRunner';

const nav = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/research', label: 'Research', icon: Building2 },
  { to: '/briefings', label: 'Briefings', icon: FileText },
];

export default function Layout({ children, onPipelineComplete }: { children: React.ReactNode; onPipelineComplete?: () => void }) {
  const { pathname } = useLocation();

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Dark navy header */}
      <header className="bg-gradient-to-r from-slate-900 to-slate-800 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <Link to="/" className="flex items-center gap-2.5 font-bold text-white text-lg tracking-tight">
            <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-blue-500 shadow-lg shadow-blue-500/25">
              <Radar className="h-4 w-4 text-white" />
            </div>
            Blackburn Command Center
          </Link>
          <nav className="flex gap-1">
            {nav.map(({ to, label, icon: Icon }) => (
              <Link
                key={to}
                to={to}
                className={`inline-flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors ${
                  pathname === to
                    ? 'bg-white/15 text-white'
                    : 'text-slate-400 hover:text-white hover:bg-white/10'
                }`}
              >
                <Icon className="h-4 w-4" />
                {label}
              </Link>
            ))}
          </nav>
        </div>
        <PipelineRunner onComplete={onPipelineComplete} />
      </header>

      <main className="p-6">{children}</main>
    </div>
  );
}
