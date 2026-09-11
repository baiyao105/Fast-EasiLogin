import { TriangleExclamation } from '@gravity-ui/icons';
import { AlertDialog, Button, Spinner, toast } from '@heroui/react';
import { useQueryClient } from '@tanstack/react-query';
import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ViewId } from '@/components/app-shell';
import { EventIdentity } from '@/components/event-identity';
import { PageHeader } from '@/components/page-header';
import { StatusPill } from '@/components/status-pill';
import { EmptyState, ErrorState, LoadingState } from '@/components/ui-states';
import {
  useAccountSummary,
  useAccounts,
  useLoginEvents,
  useLoginSummary,
  useServiceStatus,
} from '@/hooks/use-dashboard';
import type { DashboardAccount, LoginEvent } from '@/lib/types';
import { formatRelativeTime } from '@/lib/utils';

type FeedItem = {
  id: string;
  username: string;
  user_id?: string | null;
  status: string;
  error_code?: string | null;
  created_at: string;
};

export function HomePage({
  onNavigate,
}: {
  onNavigate: (view: ViewId) => void;
}) {
  const queryClient = useQueryClient();
  const service = useServiceStatus();
  const accountSummary = useAccountSummary();
  const loginSummary = useLoginSummary(24);
  const recentEvents = useLoginEvents({ page: 1, page_size: 5 });
  const accountList = useAccounts({ page: 1, page_size: 100 });
  const accountMap = useMemo(() => {
    const map = new Map<string, DashboardAccount>();
    for (const account of accountList.data?.items ?? []) {
      map.set(account.user_id, account);
    }
    return map;
  }, [accountList.data]);
  const [liveFeed, setLiveFeed] = useState<FeedItem[]>([]);
  const [streamKey, setStreamKey] = useState(0);
  const [disconnectOpen, setDisconnectOpen] = useState(false);
  const [disconnectReason, setDisconnectReason] = useState('实时连接已断开');
  const [reconnecting, setReconnecting] = useState(false);

  // 服务接口异常时也弹出断开遮罩
  useEffect(() => {
    if (service.isError) {
      setDisconnectReason(
        service.error instanceof Error
          ? service.error.message
          : '服务状态异常或不可达',
      );
      setDisconnectOpen(true);
    }
  }, [service.error, service.isError]);

  // biome-ignore lint/correctness/useExhaustiveDependencies: streamKey 用于强制重建 EventSource
  useEffect(() => {
    let closedByUnmount = false;
    const source = new EventSource('/api/v1/events', { withCredentials: true });

    source.onopen = () => {
      setDisconnectOpen(false);
    };

    source.onerror = () => {
      if (closedByUnmount) {
        return;
      }
      // CLOSED 表示浏览器已放弃自动重连
      if (source.readyState === EventSource.CLOSED) {
        setDisconnectReason('EventSource 已关闭，无法接收实时事件');
        setDisconnectOpen(true);
      }
    };

    source.addEventListener('service.snapshot', (event) => {
      try {
        const data = JSON.parse((event as MessageEvent).data) as {
          status?: string;
        };
        if (data.status) {
          void queryClient.invalidateQueries({ queryKey: ['service'] });
        }
      } catch {
        // ignore malformed snapshot
      }
    });

    source.addEventListener('login.event', (event) => {
      try {
        const data = JSON.parse((event as MessageEvent).data) as {
          username?: string;
          user_id?: string | null;
          status?: string;
          error_code?: string | null;
        };
        setLiveFeed((prev) =>
          [
            {
              id: `live-${Date.now()}-${prev.length}`,
              username: data.username || '未知用户',
              user_id: data.user_id,
              status: data.status || 'system',
              error_code: data.error_code,
              created_at: new Date().toISOString(),
            },
            ...prev,
          ].slice(0, 8),
        );
        void Promise.all([
          queryClient.invalidateQueries({ queryKey: ['login-events'] }),
          queryClient.invalidateQueries({ queryKey: ['login-summary'] }),
          queryClient.invalidateQueries({ queryKey: ['accounts-summary'] }),
        ]);
      } catch {
        // ignore malformed event
      }
    });

    return () => {
      closedByUnmount = true;
      source.close();
    };
  }, [queryClient, streamKey]);

  const handleReconnect = useCallback(async () => {
    setReconnecting(true);
    try {
      await service.refetch();
      await recentEvents.refetch();
      setStreamKey((key) => key + 1);
      if (!service.isError) {
        setDisconnectOpen(false);
        toast.success('实时通道已重连');
      } else {
        toast.warning('仍无法连接后端');
      }
    } catch (err) {
      setDisconnectReason(
        err instanceof Error ? err.message : '重连失败，请检查后端服务',
      );
      toast.danger('重连失败');
    } finally {
      setReconnecting(false);
    }
  }, [recentEvents, service]);

  const feed = useMemo(() => {
    const fromApi = (recentEvents.data?.items ?? []).map(
      (item: LoginEvent) => ({
        id: `api-${item.id}`,
        username: item.username,
        user_id: item.user_id,
        status: item.status,
        error_code: item.error_code,
        created_at: item.created_at,
      }),
    );
    const seen = new Set<string>();
    return [...liveFeed, ...fromApi]
      .filter((item) => {
        const key = `${item.username}:${item.status}:${item.created_at}`;
        if (seen.has(key)) {
          return false;
        }
        seen.add(key);
        return true;
      })
      .slice(0, 5);
  }, [liveFeed, recentEvents.data]);

  const rawServiceStatus =
    service.data?.status ?? (service.isLoading ? 'loading' : 'unknown');
  const serviceStatus =
    String(rawServiceStatus) === '200' || String(rawServiceStatus) === 'ok'
      ? 'running'
      : String(rawServiceStatus);
  const counts = loginSummary.data?.counts ?? {};
  const successCount = counts.success ?? 0;
  const failCount = Object.entries(counts)
    .filter(([key]) => key !== 'success')
    .reduce((sum, [, value]) => sum + value, 0);

  return (
    <div className="space-y-6">
      <PageHeader
        title="本地快速登录服务"
        description={
          serviceStatus === 'running'
            ? '服务运行正常，账号与登录事件均可实时管理。'
            : serviceStatus === 'loading'
              ? '正在读取服务状态…'
              : '服务状态异常或不可达，请检查设置中的网络与运行配置。'
        }
        actions={
          <>
            <Button onPress={() => onNavigate('accounts')}>管理账号</Button>
            <Button variant="secondary" onPress={() => onNavigate('activity')}>
              查看活动
            </Button>
            <Button variant="ghost" onPress={() => onNavigate('settings')}>
              服务设置
            </Button>
          </>
        }
      />

      <div className="flex flex-wrap items-center gap-2">
        <StatusPill status={serviceStatus} />
        {service.data?.listen_port ? (
          <span className="text-xs text-muted">
            端口 {service.data.listen_port}
          </span>
        ) : null}
      </div>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard
          label="账号总数"
          value={accountSummary.data?.total}
          hint="当前已保存的 Seewo 账号"
          loading={accountSummary.isLoading}
          error={
            accountSummary.error instanceof Error
              ? accountSummary.error.message
              : null
          }
        />
        <MetricCard
          label="启用账号"
          value={accountSummary.data?.active}
          hint="可用于自动登录的账号"
          loading={accountSummary.isLoading}
          error={
            accountSummary.error instanceof Error
              ? accountSummary.error.message
              : null
          }
        />
        <MetricCard
          label="24 小时成功"
          value={successCount}
          hint="登录成功次数"
          loading={loginSummary.isLoading}
          error={
            loginSummary.error instanceof Error
              ? loginSummary.error.message
              : null
          }
        />
        <MetricCard
          label="24 小时异常"
          value={failCount}
          hint="失败 / 禁用 / 系统错误"
          loading={loginSummary.isLoading}
          error={
            loginSummary.error instanceof Error
              ? loginSummary.error.message
              : null
          }
        />
      </section>

      <section className="page-card p-6">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold">最近活动</h2>
            <p className="mt-1 text-sm text-muted">最近记录视图</p>
          </div>
          <Button
            size="sm"
            variant="ghost"
            onPress={() => onNavigate('activity')}
          >
            全部活动
          </Button>
        </div>
        {recentEvents.isLoading && feed.length === 0 ? (
          <LoadingState label="加载最近活动…" />
        ) : recentEvents.error && feed.length === 0 ? (
          <ErrorState
            message={
              recentEvents.error instanceof Error
                ? recentEvents.error.message
                : '活动加载失败'
            }
            onRetry={() => recentEvents.refetch()}
          />
        ) : feed.length === 0 ? (
          <EmptyState
            title="暂无事件"
            description="服务开始处理事件后，这里会显示最新动态。"
          />
        ) : (
          <ul className="divide-y divide-separator">
            {feed.map((item) => (
              <li
                key={item.id}
                className="flex flex-col gap-2 py-3 sm:flex-row sm:items-center sm:justify-between"
              >
                <EventIdentity
                  userId={item.user_id}
                  fallbackName={item.username}
                  accountMap={accountMap}
                />
                <div className="flex items-center gap-3">
                  <span className="text-xs text-muted">
                    {formatRelativeTime(item.created_at)}
                    {item.error_code ? ` · ${item.error_code}` : ''}
                  </span>
                  <StatusPill status={item.status} />
                </div>
              </li>
            ))}
          </ul>
        )}
      </section>

      <AlertDialog isOpen={disconnectOpen} onOpenChange={setDisconnectOpen}>
        <AlertDialog.Backdrop
          className="bg-linear-to-t from-danger/90 via-danger/50 to-transparent"
          variant="blur"
          isDismissable={false}
          isKeyboardDismissDisabled
        >
          <AlertDialog.Container placement="center" size="md">
            <AlertDialog.Dialog>
              <AlertDialog.Header className="items-center text-center">
                <AlertDialog.Icon status="danger">
                  <TriangleExclamation className="size-5" />
                </AlertDialog.Icon>
                <AlertDialog.Heading>后端已断开</AlertDialog.Heading>
              </AlertDialog.Header>
              <AlertDialog.Body>
                <p className="text-sm leading-6 text-muted">
                  {disconnectReason}
                </p>
              </AlertDialog.Body>
              <AlertDialog.Footer className="flex-col-reverse">
                <Button
                  className="w-full"
                  isDisabled={reconnecting}
                  onPress={() => void handleReconnect()}
                >
                  {reconnecting ? <Spinner size="sm" /> : null}
                  {reconnecting ? '重连中...' : '重连'}
                </Button>
              </AlertDialog.Footer>
            </AlertDialog.Dialog>
          </AlertDialog.Container>
        </AlertDialog.Backdrop>
      </AlertDialog>
    </div>
  );
}

function MetricCard({
  label,
  value,
  hint,
  loading,
  error,
}: {
  label: string;
  value?: number;
  hint: string;
  loading?: boolean;
  error?: string | null;
}) {
  return (
    <div className="page-card h-full p-5">
      <div className="text-[13px] font-medium text-muted">{label}</div>
      <div className="page-metric-value mt-3">
        {loading ? '…' : error ? '—' : (value ?? 0)}
      </div>
      <div className="mt-2 text-xs leading-5 text-muted">{error ?? hint}</div>
    </div>
  );
}
