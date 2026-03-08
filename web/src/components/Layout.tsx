import { Link, useLocation } from 'react-router-dom';
import { LayoutDashboard, Building2, FileText, Mail } from 'lucide-react';
import PipelineRunner from './PipelineRunner';

const nav = [
  { to: '/', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/research', label: 'Research', icon: Building2 },
  { to: '/briefings', label: 'Briefings', icon: FileText },
];

export default function Layout({ children, onPipelineComplete }: { children: React.ReactNode; onPipelineComplete?: () => void }) {
  const { pathname } = useLocation();

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Top bar */}
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center gap-6">
          <Link to="/" className="flex items-center gap-2 font-semibold text-gray-900">
            <Mail className="h-5 w-5 text-indigo-600" />
            Email Triage
          </Link>
          <nav className="flex gap-1">
            {nav.map(({ to, label, icon: Icon }) => (
              <Link
                key={to}
                to={to}
                className={`inline-flex items-center gap-1.5 rounded px-3 py-1.5 text-sm font-medium ${
                  pathname === to
                    ? 'bg-indigo-50 text-indigo-700'
                    : 'text-gray-600 hover:bg-gray-100'
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

      {/* Content */}
      <main className="p-6">{children}</main>
    </div>
  );
}
