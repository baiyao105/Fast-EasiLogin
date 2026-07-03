import { useState } from 'react';
import { cn } from '../../lib/utils';

interface SidebarProps {
  collapsed: boolean;
  onToggle: () => void;
  currentPage: string;
  onNavigate: (page: string) => void;
}

const navItems = [
  { id: 'dashboard', label: '仪表盘', icon: '📊' },
  { id: 'accounts', label: '账户管理', icon: '👤' },
  { id: 'settings', label: '设置', icon: '⚙️' },
];

export function Sidebar({ collapsed, onToggle, currentPage, onNavigate }: SidebarProps) {
  return (
    <aside className={cn('sidebar', collapsed && 'collapsed')}>
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <div className="sidebar-logo-icon">FE</div>
          {!collapsed && <span>Fast EasiLogin</span>}
        </div>
      </div>

      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <a
            key={item.id}
            className={cn('nav-item', currentPage === item.id && 'active')}
            onClick={() => onNavigate(item.id)}
          >
            <span className="nav-item-icon">{item.icon}</span>
            {!collapsed && <span className="nav-item-label">{item.label}</span>}
          </a>
        ))}
      </nav>

      <div className="sidebar-footer">
        <button
          className="nav-item w-full"
          onClick={onToggle}
        >
          <span className="nav-item-icon">
            {collapsed ? '→' : '←'}
          </span>
          {!collapsed && <span className="nav-item-label">收起侧栏</span>}
        </button>
      </div>
    </aside>
  );
}
