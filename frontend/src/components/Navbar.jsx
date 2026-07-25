import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Compass, LogOut, User, FolderKanban, Sparkles } from 'lucide-react';

export const Navbar = () => {
  const { student, logout, isAuthenticated } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  if (!isAuthenticated) return null;

  return (
    <header className="sticky top-0 z-40 glass-panel border-b border-slate-800/80 px-4 lg:px-8 py-3.5 transition-all">
      <div className="max-w-7xl mx-auto flex items-center justify-between">
        {/* Brand Logo */}
        <Link to="/" className="flex items-center gap-3 group">
          <div className="w-10 h-10 rounded-xl gradient-button flex items-center justify-center shadow-lg group-hover:scale-105 transition-transform">
            <Compass className="w-6 h-6 text-white animate-pulse-slow" />
          </div>
          <div>
            <div className="flex items-center gap-1.5 font-extrabold text-xl tracking-tight text-white">
              Career<span className="gradient-text">Tours</span>
              <Sparkles className="w-4 h-4 text-amber-400" />
            </div>
            <p className="text-[10px] text-slate-400 font-medium tracking-wide uppercase">AI Skill & Career Guidance</p>
          </div>
        </Link>

        {/* User Navigation & Profile */}
        <div className="flex items-center gap-6">
          <Link
            to="/"
            className="hidden sm:flex items-center gap-2 text-sm font-semibold text-slate-300 hover:text-white transition-colors py-1.5 px-3 rounded-lg hover:bg-slate-800/50"
          >
            <FolderKanban className="w-4 h-4 text-brand-400" />
            Dashboard
          </Link>

          {/* Student Profile Info */}
          <div className="flex items-center gap-3 pl-4 border-l border-slate-800">
            <div className="w-9 h-9 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-brand-400 font-bold shadow-inner">
              {student?.full_name ? student.full_name.charAt(0).toUpperCase() : <User className="w-5 h-5" />}
            </div>
            <div className="hidden md:block text-left">
              <div className="text-sm font-semibold text-white leading-tight">{student?.full_name || 'Student'}</div>
              <div className="text-xs text-slate-400 font-normal">{student?.email}</div>
            </div>
            
            <button
              onClick={handleLogout}
              title="Logout"
              className="ml-2 p-2 rounded-lg text-slate-400 hover:text-red-400 hover:bg-red-950/30 border border-transparent hover:border-red-900/50 transition-all flex items-center gap-1 text-xs font-medium"
            >
              <LogOut className="w-4 h-4" />
              <span className="hidden sm:inline">Logout</span>
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Navbar;
