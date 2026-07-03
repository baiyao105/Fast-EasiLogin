import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { StatsCard } from '../components/business/stats-card';
import { useDashboardStats } from '../lib/api/hooks';

const queryClient = new QueryClient();

export function StatsIsland() {
  return (
    <QueryClientProvider client={queryClient}>
      <StatsCardInner />
    </QueryClientProvider>
  );
}

function StatsCardInner() {
  const { data, isLoading } = useDashboardStats();
  
  if (isLoading) {
    return (
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="stat-card animate-pulse">
            <div className="h-3 w-16 bg-[var(--bg-tertiary)] rounded mb-3" />
            <div className="h-8 w-20 bg-[var(--bg-tertiary)] rounded" />
          </div>
        ))}
      </div>
    );
  }
  
  return <StatsCard stats={data?.data} />;
}
