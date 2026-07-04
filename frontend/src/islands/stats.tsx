import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';
import { Card, Skeleton } from '@heroui/react';
import { StatsCard } from '../components/business/stats-card';
import { useWebSocket } from '../lib/api/websocket';
import type { DashboardStats } from '../types/api';

const queryClient = new QueryClient();

export function StatsIsland() {
  return (
    <QueryClientProvider client={queryClient}>
      <StatsCardInner />
    </QueryClientProvider>
  );
}

function StatsCardInner() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useWebSocket({
    onStats: (data) => {
      setStats(data);
      setIsLoading(false);
    },
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-3 gap-4">
        {[...Array(3)].map((_, i) => (
          <Card key={i}>
            <Card.Content className="p-5">
              <div className="flex items-start justify-between mb-4">
                <Skeleton className="h-11 w-11 rounded-xl" />
                <Skeleton className="h-6 w-16 rounded-full" />
              </div>
              <Skeleton className="h-4 w-20 rounded mb-2" />
              <Skeleton className="h-8 w-24 rounded" />
            </Card.Content>
          </Card>
        ))}
      </div>
    );
  }

  return <StatsCard stats={stats} />;
}
