import { useState } from 'react';
import { cn } from '../../lib/utils';
import { Sidebar } from './sidebar';

interface LayoutProps {
  children: React.ReactNode;
}

export function Layout({ children }: LayoutProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [currentPage, setCurrentPage] = useState('dashboard');

  return (
    <div className="flex min-h-screen">
      <Sidebar
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
        currentPage={currentPage}
        onNavigate={setCurrentPage}
      />

      <main
        className={cn(
          'main-content flex-1',
          sidebarCollapsed && 'sidebar-collapsed'
        )}
      >
        {children}
      </main>
    </div>
  );
}
