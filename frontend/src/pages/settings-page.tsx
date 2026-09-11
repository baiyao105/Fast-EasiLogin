import {
  Key,
  Power,
  Server,
  ShieldCheck,
  TriangleExclamation,
} from '@gravity-ui/icons';
import {
  Button,
  Card,
  Description,
  Input,
  Label,
  Switch,
  TextField,
  toast,
} from '@heroui/react';
import { useEffect, useRef, useState } from 'react';
import { ConfirmDialog } from '@/components/confirm-dialog';
import { PageHeader } from '@/components/page-header';
import { ErrorState, LoadingState } from '@/components/ui-states';
import {
  usePatchSettings,
  useRestartService,
  useRotateEncryption,
  useSettings,
  useStopService,
} from '@/hooks/use-dashboard';

type PendingAction = 'restart' | 'stop' | 'rotate' | null;

function SectionIcon({
  children,
  tone = 'accent',
}: {
  children: React.ReactNode;
  tone?: 'accent' | 'success' | 'warning' | 'danger';
}) {
  const tones = {
    accent: 'bg-accent/10 text-accent',
    success: 'bg-success/10 text-success',
    warning: 'bg-warning/10 text-warning',
    danger: 'bg-danger/10 text-danger',
  } as const;
  return (
    <span
      className={`flex size-9 shrink-0 items-center justify-center rounded-xl ${tones[tone]}`}
    >
      {children}
    </span>
  );
}

function SettingRow({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-3 border-b border-separator py-4 last:border-b-0 sm:flex-row sm:items-center sm:justify-between sm:gap-6">
      <div className="min-w-0 sm:max-w-md">
        <div className="text-sm font-medium text-foreground">{title}</div>
        {description ? (
          <div className="mt-0.5 text-xs leading-5 text-muted">
            {description}
          </div>
        ) : null}
      </div>
      <div className="shrink-0 sm:w-64">{children}</div>
    </div>
  );
}

export function SettingsPage() {
  const settings = useSettings();
  const patchSettings = usePatchSettings();
  const rotateEncryption = useRotateEncryption();
  const restartService = useRestartService();
  const stopService = useStopService();

  const [apiPort, setApiPort] = useState('');
  const [dashboardHost, setDashboardHost] = useState('');
  const [dashboardPort, setDashboardPort] = useState('');
  const [sessionTtl, setSessionTtl] = useState('');
  const [enableEventlog, setEnableEventlog] = useState(true);
  const [autoRestart, setAutoRestart] = useState(true);
  const [restartDelay, setRestartDelay] = useState('0');
  const [passwordErrorDisable, setPasswordErrorDisable] = useState(false);
  const [pending, setPending] = useState<PendingAction>(null);
  const [recovering, setRecovering] = useState<'restart' | 'stop' | null>(null);
  const [dirty, setDirty] = useState(false);
  const lastSeededAt = useRef(0);

  useEffect(() => {
    if (!settings.data || dirty) {
      return;
    }
    if (
      lastSeededAt.current === settings.dataUpdatedAt &&
      lastSeededAt.current !== 0
    ) {
      return;
    }
    setApiPort(String(settings.data.network.api_port));
    setDashboardHost(settings.data.network.dashboard_host);
    setDashboardPort(String(settings.data.network.dashboard_port));
    setSessionTtl(String(settings.data.authentication.session_ttl_seconds));
    setEnableEventlog(Boolean(settings.data.runtime.enable_eventlog));
    setAutoRestart(Boolean(settings.data.runtime.auto_restart_on_crash));
    setRestartDelay(String(settings.data.runtime.restart_delay_seconds));
    setPasswordErrorDisable(
      Boolean(settings.data.authentication.enable_password_error_disable),
    );
    lastSeededAt.current = settings.dataUpdatedAt;
  }, [dirty, settings.data, settings.dataUpdatedAt]);

  function markDirty() {
    setDirty(true);
  }

  async function saveAll() {
    try {
      const result = await patchSettings.mutateAsync({
        network: {
          api_port: Number(apiPort),
          dashboard_host: dashboardHost,
          dashboard_port: Number(dashboardPort),
        },
        runtime: {
          enable_eventlog: enableEventlog,
          auto_restart_on_crash: autoRestart,
          restart_delay_seconds: Number(restartDelay),
        },
        authentication: {
          session_ttl_seconds: Number(sessionTtl),
          enable_password_error_disable: passwordErrorDisable,
        },
      });
      if (result.restart_required) {
        toast.warning('设置已保存，网络变更需重启服务后生效');
      } else {
        toast.success('设置已保存');
      }
      setDirty(false);
    } catch (err) {
      toast.danger(err instanceof Error ? err.message : '保存失败');
    }
  }

  function resetForm() {
    if (!settings.data) {
      return;
    }
    setApiPort(String(settings.data.network.api_port));
    setDashboardHost(settings.data.network.dashboard_host);
    setDashboardPort(String(settings.data.network.dashboard_port));
    setSessionTtl(String(settings.data.authentication.session_ttl_seconds));
    setEnableEventlog(Boolean(settings.data.runtime.enable_eventlog));
    setAutoRestart(Boolean(settings.data.runtime.auto_restart_on_crash));
    setRestartDelay(String(settings.data.runtime.restart_delay_seconds));
    setPasswordErrorDisable(
      Boolean(settings.data.authentication.enable_password_error_disable),
    );
    setDirty(false);
  }

  async function handleRotate() {
    const source = settings.data?.encryption.key_source ?? 'dpapi';
    try {
      const result = await rotateEncryption.mutateAsync(source);
      toast.success(`已轮换加密密钥，版本 ${result.key_version}`);
      setPending(null);
    } catch (err) {
      toast.danger(err instanceof Error ? err.message : '轮换失败');
    }
  }

  async function handleRestart() {
    try {
      await restartService.mutateAsync();
      setRecovering('restart');
      toast.info('重启指令已接受，正在等待服务恢复');
      setPending(null);
      window.setTimeout(() => {
        setRecovering(null);
        void settings.refetch();
      }, 2500);
    } catch (err) {
      toast.danger(err instanceof Error ? err.message : '重启失败');
    }
  }

  async function handleStop() {
    try {
      await stopService.mutateAsync();
      setRecovering('stop');
      toast.warning('停止指令已接受，服务连接将中断');
      setPending(null);
    } catch (err) {
      toast.danger(err instanceof Error ? err.message : '停止失败');
    }
  }

  if (settings.isLoading) {
    return <LoadingState label="加载设置…" />;
  }

  if (settings.error) {
    return (
      <ErrorState
        message={
          settings.error instanceof Error
            ? settings.error.message
            : '设置加载失败'
        }
        onRetry={() => settings.refetch()}
      />
    );
  }

  return (
    <div className="relative flex flex-col gap-6 pb-20">
      <PageHeader
        title="设置"
        description="管理网络、运行时与安全选项。危险操作会二次确认。"
      />

      {recovering ? (
        <div className="flex items-center gap-2 rounded-xl border border-warning/20 bg-warning/10 px-4 py-3 text-sm text-warning">
          <TriangleExclamation className="size-4 shrink-0" aria-hidden />
          {recovering === 'restart'
            ? '服务重启中，连接恢复后会自动刷新状态。'
            : '服务已请求停止，部分接口可能暂时不可用。'}
        </div>
      ) : null}

      <Card>
        <Card.Header className="flex-row items-center gap-3">
          <SectionIcon>
            <Server className="size-4.5" aria-hidden />
          </SectionIcon>
          <div>
            <Card.Title>网络</Card.Title>
            <Card.Description>
              修改端口或监听地址后需重启服务才会生效
            </Card.Description>
          </div>
        </Card.Header>
        <Card.Content className="px-2 sm:px-6">
          <SettingRow title="API 端口" description="上游快速登录服务监听端口">
            <TextField fullWidth>
              <Label className="sr-only">API 端口</Label>
              <Input
                type="number"
                value={apiPort}
                onChange={(event) => {
                  setApiPort(event.target.value);
                  markDirty();
                }}
                variant="secondary"
              />
            </TextField>
          </SettingRow>
          <SettingRow
            title="控制台主机"
            description="WebUI 绑定地址，通常保持 127.0.0.1"
          >
            <TextField fullWidth>
              <Label className="sr-only">控制台主机</Label>
              <Input
                value={dashboardHost}
                onChange={(event) => {
                  setDashboardHost(event.target.value);
                  markDirty();
                }}
                variant="secondary"
              />
            </TextField>
          </SettingRow>
          <SettingRow title="控制台端口" description="浏览器访问的 WebUI 端口">
            <TextField fullWidth>
              <Label className="sr-only">控制台端口</Label>
              <Input
                type="number"
                value={dashboardPort}
                onChange={(event) => {
                  setDashboardPort(event.target.value);
                  markDirty();
                }}
                variant="secondary"
              />
            </TextField>
          </SettingRow>
        </Card.Content>
      </Card>

      <Card>
        <Card.Header className="flex-row items-center gap-3">
          <SectionIcon tone="success">
            <Power className="size-4.5" aria-hidden />
          </SectionIcon>
          <div>
            <Card.Title>运行时</Card.Title>
            <Card.Description>服务稳定性与日志相关选项</Card.Description>
          </div>
        </Card.Header>
        <Card.Content className="px-2 sm:px-6">
          <SettingRow
            title="启用登录事件日志"
            description="记录每次登录成功/失败，用于活动页展示"
          >
            <div className="flex justify-end">
              <Switch
                isSelected={enableEventlog}
                onChange={(value) => {
                  setEnableEventlog(value);
                  markDirty();
                }}
              >
                <Label>{enableEventlog ? '已开启' : '已关闭'}</Label>
              </Switch>
            </div>
          </SettingRow>
          <SettingRow
            title="崩溃后自动重启"
            description="进程异常退出后按延迟自动拉起"
          >
            <div className="flex justify-end">
              <Switch
                isSelected={autoRestart}
                onChange={(value) => {
                  setAutoRestart(value);
                  markDirty();
                }}
              >
                <Label>{autoRestart ? '已开启' : '已关闭'}</Label>
              </Switch>
            </div>
          </SettingRow>
          <SettingRow title="崩溃重启延迟" description="自动重启前等待的秒数">
            <TextField fullWidth>
              <Label className="sr-only">崩溃重启延迟（秒）</Label>
              <Input
                type="number"
                value={restartDelay}
                onChange={(event) => {
                  setRestartDelay(event.target.value);
                  markDirty();
                }}
                variant="secondary"
              />
            </TextField>
          </SettingRow>
        </Card.Content>
      </Card>

      <Card>
        <Card.Header className="flex-row items-center gap-3">
          <SectionIcon tone="warning">
            <ShieldCheck className="size-4.5" aria-hidden />
          </SectionIcon>
          <div>
            <Card.Title>安全</Card.Title>
            <Card.Description>会话与账号保护策略</Card.Description>
          </div>
        </Card.Header>
        <Card.Content className="px-2 sm:px-6">
          <SettingRow
            title="会话有效期"
            description="控制台登录 Cookie 的有效时长（秒）"
          >
            <TextField fullWidth>
              <Label className="sr-only">会话有效期（秒）</Label>
              <Input
                type="number"
                value={sessionTtl}
                onChange={(event) => {
                  setSessionTtl(event.target.value);
                  markDirty();
                }}
                variant="secondary"
              />
            </TextField>
          </SettingRow>
          <SettingRow
            title="密码错误自动禁用"
            description="密码错误次数过多时自动停用该 Seewo 账号"
          >
            <div className="flex justify-end">
              <Switch
                isSelected={passwordErrorDisable}
                onChange={(value) => {
                  setPasswordErrorDisable(value);
                  markDirty();
                }}
              >
                <Label>{passwordErrorDisable ? '已开启' : '已关闭'}</Label>
              </Switch>
            </div>
          </SettingRow>
        </Card.Content>
      </Card>

      <Card className="border-danger/20">
        <Card.Header className="flex-row items-center gap-3">
          <SectionIcon tone="danger">
            <Key className="size-4.5" aria-hidden />
          </SectionIcon>
          <div>
            <Card.Title className="text-danger">危险区域</Card.Title>
            <Card.Description>
              当前密钥：{settings.data?.encryption.key_source ?? '—'} · 版本{' '}
              {settings.data?.encryption.key_version ?? '—'}
            </Card.Description>
          </div>
        </Card.Header>
        <Card.Content>
          <div className="flex flex-col gap-3 sm:flex-row sm:flex-wrap">
            <Button variant="secondary" onPress={() => setPending('rotate')}>
              轮换加密密钥
            </Button>
            <Button variant="secondary" onPress={() => setPending('restart')}>
              重启服务
            </Button>
            <Button variant="danger" onPress={() => setPending('stop')}>
              停止服务
            </Button>
          </div>
          <Description className="mt-3 text-xs text-muted">
            轮换密钥会重新加密本地凭据；重启/停止会短暂中断服务。
          </Description>
        </Card.Content>
      </Card>

      {dirty ? (
        <div className="fixed inset-x-0 bottom-0 z-40 border-t border-separator bg-background/90 backdrop-blur">
          <div className="mx-auto flex max-w-6xl items-center justify-between gap-3 px-4 py-3 md:px-6">
            <span className="text-sm text-muted">有未保存的更改</span>
            <div className="flex gap-2">
              <Button variant="ghost" onPress={resetForm}>
                放弃
              </Button>
              <Button
                isDisabled={patchSettings.isPending}
                onPress={() => void saveAll()}
              >
                {patchSettings.isPending ? '保存中…' : '保存更改'}
              </Button>
            </div>
          </div>
        </div>
      ) : null}

      <ConfirmDialog
        open={pending === 'rotate'}
        onOpenChange={(open) => !open && setPending(null)}
        title="轮换加密密钥"
        description="将使用当前密钥来源重新加密本地凭据。过程中服务可能短暂不可用。"
        confirmLabel="继续轮换"
        loading={rotateEncryption.isPending}
        status="warning"
        onConfirm={() => void handleRotate()}
      />
      <ConfirmDialog
        open={pending === 'restart'}
        onOpenChange={(open) => !open && setPending(null)}
        title="重启服务"
        description="将中断当前连接并重启本地快速登录服务。确认继续？"
        confirmLabel="重启"
        loading={restartService.isPending}
        status="warning"
        onConfirm={() => void handleRestart()}
      />
      <ConfirmDialog
        open={pending === 'stop'}
        onOpenChange={(open) => !open && setPending(null)}
        title="停止服务"
        description="停止后自动登录将不可用，控制台也会失去服务状态。确认停止？"
        confirmLabel="停止"
        loading={stopService.isPending}
        status="danger"
        onConfirm={() => void handleStop()}
      />
    </div>
  );
}
