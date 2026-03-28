'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { MessageSquare, FileText, Zap, BarChart3, Settings, ChevronDown } from 'lucide-react';

export function DashboardSidebar() {
  const [expandedSection, setExpandedSection] = useState<string | null>('applications');

  const navItems = [
    { icon: MessageSquare, label: 'Chat Agent', href: '/dashboard', section: 'chat' },
    { icon: FileText, label: 'Applications', href: '/dashboard/applications', section: 'applications' },
    { icon: Zap, label: 'Quick Apply', href: '/dashboard/quick-apply', section: 'quick' },
    { icon: BarChart3, label: 'Analytics', href: '/dashboard/analytics', section: 'analytics' },
    { icon: Settings, label: 'Settings', href: '/dashboard/settings', section: 'settings' },
  ];

  return (
    <aside className="hidden lg:flex flex-col w-64 bg-card/30 border-r border-border/40 p-4 space-y-4">
      {/* Logo */}
      <div className="mb-6">
        <h2 className="text-sm font-bold text-foreground/80 px-4">Menu</h2>
      </div>

      {/* Navigation */}
      <nav className="space-y-2 flex-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.section}
              href={item.href}
              className="flex items-center gap-3 px-4 py-3 rounded-lg hover:bg-card/80 transition group text-foreground/70 hover:text-foreground"
            >
              <Icon className="w-5 h-5" />
              <span className="font-medium">{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Stats */}
      <div className="border-t border-border/40 pt-4 space-y-3">
        <div className="p-3 rounded-lg bg-card/50 border border-border/40">
          <p className="text-xs text-foreground/60 mb-1">Applications This Week</p>
          <p className="text-2xl font-bold text-primary">12</p>
        </div>
        <div className="p-3 rounded-lg bg-card/50 border border-border/40">
          <p className="text-xs text-foreground/60 mb-1">Response Rate</p>
          <p className="text-2xl font-bold text-accent">68%</p>
        </div>
      </div>
    </aside>
  );
}
