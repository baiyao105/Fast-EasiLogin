import { Toast } from '@heroui/react';
import { useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useState } from 'react';
import { AppShell, type ViewId } from '@/components/app-shell';
import { SignInGate } from '@/components/sign-in-gate';
import { ErrorState, LoadingState } from '@/components/ui-states';
import { useAuthStatus, useLogout } from '@/hooks/use-dashboard';
import { setUnauthorizedHandler } from '@/lib/api';
import { readHashView, writeHashView } from '@/lib/utils';
import { AccountsPage } from '@/pages/accounts-page';
import { ActivityPage } from '@/pages/activity-page';
import { HomePage } from '@/pages/home-page';
import { SettingsPage } from '@/pages/settings-page';

const VALID_VIEWS: ViewId[] = ['home', 'accounts', 'activity', 'settings'];

function coerceView(value: string): ViewId {
  return (VALID_VIEWS as string[]).includes(value) ? (value as ViewId) : 'home';
}

export default function App() {
  const queryClient = useQueryClient();
  const auth = useAuthStatus();
  const logout = useLogout();
  const [view, setView] = useState<ViewId>(() => coerceView(readHashView()));

  useEffect(() => {
    setUnauthorizedHandler(() => {
      void queryClient.invalidateQueries({ queryKey: ['auth-status'] });
    });
    return () => setUnauthorizedHandler(null);
  }, [queryClient]);

  useEffect(() => {
    const onHashChange = () => setView(coerceView(readHashView()));
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  const handleViewChange = useCallback((next: ViewId) => {
    setView(next);
    writeHashView(next);
  }, []);

  const needsGate =
    Boolean(auth.data?.password_required) && !auth.data?.authenticated;

  return (
    <>
      <Toast.Provider className="z-[10000]" placement="bottom end" />
      {auth.isLoading ? (
        <div className="flex min-h-dvh items-center justify-center bg-background p-6">
          <div className="w-full max-w-md">
            <LoadingState label="检查登录状态…" />
          </div>
        </div>
      ) : auth.error ? (
        <div className="flex min-h-dvh items-center justify-center bg-background p-6">
          <div className="w-full max-w-md">
            <ErrorState
              message={
                auth.error instanceof Error
                  ? auth.error.message
                  : '无法连接控制台服务'
              }
              onRetry={() => auth.refetch()}
            />
          </div>
        </div>
      ) : needsGate ? (
        <SignInGate onComplete={() => auth.refetch()} />
      ) : (
        <AppShell
          view={view}
          onViewChange={handleViewChange}
          onLogout={() => logout.mutate()}
          logoutBusy={logout.isPending}
        >
          {view === 'home' ? <HomePage onNavigate={handleViewChange} /> : null}
          {view === 'accounts' ? <AccountsPage /> : null}
          {view === 'activity' ? <ActivityPage /> : null}
          {view === 'settings' ? <SettingsPage /> : null}
        </AppShell>
      )}
    </>
  );
}
