import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Compass, LogOut, User, FolderKanban, Sparkles } from 'lucide-react';
import ThemeToggle from './ThemeToggle';

export const Navbar = () => {
  const { student, logout, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  if (!isAuthenticated) return null;

  return (
    <header className="sticky top-0 z-40 surface-glass border-b border-line/80 px-4 lg:px-8 py-3.5 transition-all">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        {/* Brand Logo */}
        <Link to="/" className="flex items-center gap-3 group">
          <div className="w-10 h-10 rounded-xl btn-brand flex items-center justify-center shadow-lg group-hover:scale-105 transition-transform">
            <Compass className="w-6 h-6 text-fg-on-solid" aria-hidden="true" />
          </div>
          <div>
            <div className="flex items-center gap-1.5 font-extrabold text-xl tracking-tight text-fg">
              Career<span className="text-gradient">Tours</span>
              <Sparkles className="w-4 h-4 text-warning-fg" aria-hidden="true" />
            </div>
            <p className="text-2xs text-fg-muted font-medium tracking-wide uppercase">AI Skill & Career Guidance</p>
          </div>
        </Link>

        {/* User Navigation & Profile */}
        <div className="flex items-center gap-6">
          <Link
            to="/"
            className="hidden sm:flex items-center gap-2 text-sm font-semibold text-fg-secondary hover:text-fg transition-colors py-1.5 px-3 rounded-lg hover:bg-surface-2/50"
          >
            <FolderKanban className="w-4 h-4 text-brand-fg" aria-hidden="true" />
            Dashboard
          </Link>

          <ThemeToggle />

          {/* Student Profile Info */}
          <div className="flex items-center gap-3 pl-4 border-l border-line">
            <div className="w-9 h-9 rounded-full bg-surface-2 border border-line-strong flex items-center justify-center text-brand-fg font-bold shadow-inner">
              {student?.full_name ? student.full_name.charAt(0).toUpperCase() : <User className="w-5 h-5" />}
            </div>
            <div className="hidden md:block text-left">
              <div className="text-sm font-semibold text-fg leading-tight">{student?.full_name || 'Student'}</div>
              <div className="text-xs text-fg-muted font-normal">{student?.email}</div>
            </div>
            
            {/* aria-label rather than relying on the label span: that span is
                hidden below 640px, which left the button with no accessible
                name at all on mobile. */}
            <button
              type="button"
              onClick={handleLogout}
              aria-label="Log out"
              className="ml-2 p-2 rounded-lg text-fg-muted hover:text-danger-fg hover:bg-danger-subtle/30 border border-transparent hover:border-danger-fg/50 transition-all flex items-center gap-1 text-xs font-medium"
            >
              <LogOut className="w-4 h-4" aria-hidden="true" />
              <span className="hidden sm:inline">Logout</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Navbar;
