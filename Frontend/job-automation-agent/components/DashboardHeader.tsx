'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { useAuth } from '@/context/AuthContext';
import { LogOut, User, Settings, Menu, X } from 'lucide-react';
import { useRouter } from 'next/navigation';

export function DashboardHeader() {
  const { user, userProfile, logout } = useAuth();
  const router = useRouter();
  const [menuOpen, setMenuOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    router.push('/');
  };

  return (
    <header className="sticky top-0 z-40 bg-card/50 border-b border-border/40 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
        {/* Logo */}
        <div className="flex items-center gap-2">
          <div className="w-10 h-10 rounded-lg bg-gradient-to-br from-primary to-accent flex items-center justify-center">
            <span className="text-white font-bold text-lg">JA</span>
          </div>
          <h1 className="text-xl font-bold bg-gradient-to-r from-primary to-accent bg-clip-text text-transparent hidden sm:block">
            JobAgent
          </h1>
        </div>

        {/* Desktop Menu */}
        <div className="hidden md:flex items-center gap-2">
          <div className="flex items-center gap-3 px-4 py-2 rounded-lg bg-card/80 border border-border/40">
            <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
              <span className="text-sm font-semibold text-primary">
                {userProfile?.displayName?.charAt(0).toUpperCase() || 'U'}
              </span>
            </div>
            <div className="hidden lg:block">
              <p className="text-sm font-medium">{userProfile?.displayName || 'User'}</p>
              <p className="text-xs text-foreground/60">{user?.email}</p>
            </div>
          </div>

          <Link href="/dashboard/settings" className="p-2 hover:bg-card/80 rounded-lg transition">
            <Settings className="w-5 h-5 text-foreground/60 hover:text-foreground" />
          </Link>

          <button
            onClick={handleLogout}
            className="p-2 hover:bg-destructive/10 rounded-lg transition text-foreground/60 hover:text-destructive"
          >
            <LogOut className="w-5 h-5" />
          </button>
        </div>

        {/* Mobile Menu Button */}
        <button
          onClick={() => setMenuOpen(!menuOpen)}
          className="md:hidden p-2 hover:bg-card/80 rounded-lg transition"
        >
          {menuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile Menu */}
      {menuOpen && (
        <div className="md:hidden border-t border-border/40 bg-card/30 p-4 space-y-3">
          <div className="flex items-center gap-3 p-3 rounded-lg bg-card/80 border border-border/40">
            <div className="w-8 h-8 rounded-full bg-primary/20 flex items-center justify-center">
              <span className="text-sm font-semibold text-primary">
                {userProfile?.displayName?.charAt(0).toUpperCase() || 'U'}
              </span>
            </div>
            <div>
              <p className="text-sm font-medium">{userProfile?.displayName || 'User'}</p>
              <p className="text-xs text-foreground/60">{user?.email}</p>
            </div>
          </div>

          <Link href="/dashboard/settings" className="flex items-center gap-2 px-4 py-2 hover:bg-card/80 rounded-lg transition">
            <Settings className="w-5 h-5" />
            <span>Settings</span>
          </Link>

          <button
            onClick={handleLogout}
            className="w-full flex items-center gap-2 px-4 py-2 hover:bg-destructive/10 rounded-lg transition text-destructive"
          >
            <LogOut className="w-5 h-5" />
            <span>Logout</span>
          </button>
        </div>
      )}
    </header>
  );
}
