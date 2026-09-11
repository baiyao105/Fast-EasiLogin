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
  FieldError,
  Input,
  Label,
  Spinner,
  TextField,
  toast,
} from '@heroui/react';
import { useEffect, useRef, useState } from 'react';
import { ConfirmDialog } from '@/components/confirm-dialog';
import { PageHeader } from '@/components/page-header';
import { SetPasswordDialog } from '@/components/set-password-dialog';
import { ErrorState, LoadingState } from '@/components/ui-states';
import {
  usePatchSettings,
  useRestartService,
  useRotateEncryption,
  useSettings,
  useStopService,
} from '@/hooks/use-dashboard';

type PendingAction = 'restart' | 'stop' | 'rotate' | null;

const LOOPBACK = new Set(['127.0.0.1', 'localhost', '::1', '']);
const HOST_RE =
  /^(\d{1,3}\.){3}\d{1,3}$|^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*$/;

function isLoopback(host: string): boolean {
  return LOOPBACK.has(host.trim().toLowerCase());
}

function isValidHost(host: string): boolean {
  const h = host.trim();
  if (!h) return false;
  if (h === '0.0.0.0' || h === '::' || h === '[::]') return true;
  if (!HOST_RE.test(h)) return false;
  // IPv4 四段 0-255
  if (/^(\d{1,3}\.){3}\d{1,3}$/.test(h)) {
    return h.split('.').every((p) => Number(p) >= 0 && Number(p) <= 255);
  }
  return true;
}

function isValidPort(v: string): boolean {
  const n = Number(v);
  return Number.isInteger(n) && n >= 1024 && n <= 65535;
}

function SectionIcon({
  children,
  tone = 'accent',
}: {
  children: React.ReactNode;
  tone?: 'accent' | 'warning' | 'danger';
}) {
  const tones = {
    accent: 'bg-accent/10 text-accent',
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
      <div className="shrink-0 sm:w-72">{children}</div>
    </div>
  );
}

function useDebouncedSave(fn: () => void, delay = 3000) {
  const timer = useRef<number | null>(null);
  const fnRef = useRef(fn);
  fnRef.current = fn;
  return () => {
    if (timer.current) window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => fnRef.current(), delay);
  };
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
  const [pending, setPending] = useState<PendingAction>(null);
  const [recovering, setRecovering] = useState<'restart' | 'stop' | null>(null);
  const [passwordDialog, setPasswordDialog] = useState(false);
  const [passwordSet, setPasswordSet] = useState(false);
  const seededAt = useRef(0);

  const [hostError, setHostError] = useState<string | null>(null);
  const [apiPortError, setApiPortError] = useState<string | null>(null);
  const [dashPortError, setDashPortError] = useState<string | null>(null);
  const [ttlError, setTtlError] = useState<string | null>(null);

  const loopback = isLoopback(dashboardHost);
  const remoteWarning = !loopback;

  useEffect(() => {
    if (!settings.data) return;
    if (seededAt.current === settings.dataUpdatedAt) return;
    setApiPort(String(settings.data.network.api_port));
    setDashboardHost(settings.data.network.dashboard_host);
    setDashboardPort(String(settings.data.network.dashboard_port));
    setSessionTtl(String(settings.data.authentication.session_ttl_seconds));
    setPasswordSet(Boolean(settings.data.authentication.password_set));
    seededAt.current = settings.dataUpdatedAt;
  }, [settings.data, settings.dataUpdatedAt]);

  async function saveNetwork(host = dashboardHost) {
    if (!isValidHost(host)) {
      setHostError('请输入有效的主机地址');
      return;
    }
    if (!isValidPort(apiPort)) {
      setApiPortError('端口需在 1024–65535');
      return;
    }
    if (!isValidPort(dashboardPort)) {
      setDashPortError('端口需在 1024–65535');
      return;
    }
    setHostError(null);
    setApiPortError(null);
    setDashPortError(null);

    if (!isLoopback(host) && !passwordSet) {
      setPasswordDialog(true);
      return;
    }

    try {
      const result = await patchSettings.mutateAsync({
        network: {
          api_port: Number(apiPort),
          dashboard_host: host.trim(),
          dashboard_port: Number(dashboardPort),
        },
      });
      if (result.restart_required) {
        toast.warning('已保存，网络变更需重启服务后生效');
      } else {
        toast.success('网络配置已保存');
      }
      setPasswordSet(Boolean(result.settings?.authentication.password_set));
    } catch (err) {
      toast.danger(err instanceof Error ? err.message : '保存失败');
    }
  }

  const debouncedNetwork = useDebouncedSave(() => void saveNetwork(), 3000);
  const debouncedTtl = useDebouncedSave(() => {
    const ttl = Number(sessionTtl);
    if (!Number.isInteger(ttl) || ttl < 60 || ttl > 30 * 86400) {
      setTtlError('需在 60 秒 ~ 30 天之间');
      return;
    }
    setTtlError(null);
    void patchSettings
      .mutateAsync({ authentication: { session_ttl_seconds: ttl } })
      .then(() => toast.success('会话有效期已保存'))
      .catch((err) =>
        toast.danger(err instanceof Error ? err.message : '保存失败'),
      );
  }, 3000);

  async function handleRotate() {
    const source = settings.data?.encryption.key_source ?? 'environment';
    try {
      const result = await rotateEncryption.mutateAsync(source);
      toast.success(
        `已轮换密钥，版本 ${result.key_version}，已重新加密 ${result.rotated} 条凭据`,
      );
      setPending(null);
    } catch (err) {
      toast.danger(err instanceof Error ? err.message : '轮换失败');
    }
  }

  async function handleRestart() {
    try {
      await restartService.mutateAsync();
      setRecovering('restart');
      toast.info('重启指令已接受');
      setPending(null);
      window.setTimeout(() => {
        setRecovering(null);
        void settings.refetch();
      }, 3000);
    } catch (err) {
      toast.danger(err instanceof Error ? err.message : '重启失败');
    }
  }

  async function handleStop() {
    try {
      await stopService.mutateAsync();
      setRecovering('stop');
      toast.warning('停止指令已接受');
      setPending(null);
    } catch (err) {
      toast.danger(err instanceof Error ? err.message : '停止失败');
    }
  }

  if (settings.isLoading) return <LoadingState label="加载设置…" />;
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
    <div className="flex flex-col gap-6">
      <PageHeader title="设置" description="修改后 3 秒自动保存。" />

      {recovering ? (
        <div className="flex items-center gap-2 rounded-xl border border-warning/20 bg-warning/10 px-4 py-3 text-sm text-warning">
          <TriangleExclamation className="size-4 shrink-0" aria-hidden />
          {recovering === 'restart'
            ? '服务重启中，请稍候…'
            : '服务已停止，部分接口可能不可用。'}
        </div>
      ) : null}

      {/* 网络 */}
      <Card>
        <Card.Header className="flex-row items-center gap-3">
          <SectionIcon>
            <Server className="size-4.5" aria-hidden />
          </SectionIcon>
          <div>
            <Card.Title>网络</Card.Title>
            <Card.Description>
              修改后需重启服务生效；非回环地址必须先设定密码
            </Card.Description>
          </div>
        </Card.Header>
        <Card.Content className="px-2 sm:px-6">
          <SettingRow
            title="API 端口"
            description="1024–65535，上游快速登录服务端口"
          >
            <TextField fullWidth isInvalid={Boolean(apiPortError)}>
              <Label className="sr-only">API 端口</Label>
              <Input
                type="number"
                value={apiPort}
                onChange={(e) => {
                  setApiPort(e.target.value);
                  setApiPortError(null);
                  debouncedNetwork();
                }}
                variant="secondary"
              />
              <FieldError>{apiPortError}</FieldError>
            </TextField>
          </SettingRow>
          <SettingRow
            title="控制台主机"
            description="127.0.0.1 仅本机；0.0.0.0 对外暴露"
          >
            <TextField fullWidth isInvalid={Boolean(hostError)}>
              <Label className="sr-only">控制台主机</Label>
              <Input
                value={dashboardHost}
                onChange={(e) => {
                  setDashboardHost(e.target.value);
                  setHostError(null);
                  debouncedNetwork();
                }}
                variant="secondary"
              />
              <FieldError>{hostError}</FieldError>
            </TextField>
          </SettingRow>
          <SettingRow
            title="控制台端口"
            description="WebUI 访问端口，1024–65535"
          >
            <TextField fullWidth isInvalid={Boolean(dashPortError)}>
              <Label className="sr-only">控制台端口</Label>
              <Input
                type="number"
                value={dashboardPort}
                onChange={(e) => {
                  setDashboardPort(e.target.value);
                  setDashPortError(null);
                  debouncedNetwork();
                }}
                variant="secondary"
              />
              <FieldError>{dashPortError}</FieldError>
            </TextField>
          </SettingRow>
          {remoteWarning ? (
            <div className="mt-3 flex items-start gap-2 rounded-xl border border-warning/30 bg-warning/10 px-4 py-3 text-sm text-warning">
              <TriangleExclamation
                className="mt-0.5 size-4 shrink-0"
                aria-hidden
              />
              <div>
                非本机回环地址将对外可访问，
                <strong>必须先设定控制台密码</strong>才能保存。
              </div>
            </div>
          ) : null}
        </Card.Content>
      </Card>

      {/* 安全 */}
      <Card>
        <Card.Header className="flex-row items-center gap-3">
          <SectionIcon tone="warning">
            <ShieldCheck className="size-4.5" aria-hidden />
          </SectionIcon>
          <div>
            <Card.Title>安全</Card.Title>
            <Card.Description>会话与控制台访问控制</Card.Description>
          </div>
        </Card.Header>
        <Card.Content className="px-2 sm:px-6">
          <SettingRow
            title="控制台密码"
            description={
              passwordSet
                ? '访问控制台时需输入密码。如需更换请点击右侧按钮。'
                : '访问控制台时需输入密码。尚未设置。'
            }
          >
            <div className="flex justify-end">
              <Button
                variant="secondary"
                onPress={() => setPasswordDialog(true)}
              >
                {passwordSet ? '更换密码' : '设定密码'}
              </Button>
            </div>
          </SettingRow>
          <SettingRow
            title="会话有效期"
            description="60 秒 ~ 30 天，修改后 3 秒自动保存（秒）"
          >
            <TextField fullWidth isInvalid={Boolean(ttlError)}>
              <Label className="sr-only">会话有效期（秒）</Label>
              <Input
                type="number"
                min={60}
                max={2592000}
                value={sessionTtl}
                onChange={(e) => {
                  setSessionTtl(e.target.value);
                  setTtlError(null);
                  debouncedTtl();
                }}
                variant="secondary"
              />
              <FieldError>{ttlError}</FieldError>
            </TextField>
          </SettingRow>
        </Card.Content>
      </Card>

      {/* 密钥管理 */}
      <Card>
        <Card.Header className="flex-row items-center gap-3">
          <SectionIcon tone="warning">
            <Key className="size-4.5" aria-hidden />
          </SectionIcon>
          <div>
            <Card.Title>密钥管理</Card.Title>
            <Card.Description>
              当前：{settings.data?.encryption.key_source ?? '—'} · 版本{' '}
              {settings.data?.encryption.key_version ?? '—'}
            </Card.Description>
          </div>
        </Card.Header>
        <Card.Content>
          <Description className="mb-3 text-xs text-muted">
            轮换使用同一密钥材料提升版本号，并重新加密本地凭据。更换存储位置或密钥请重新运行
            OOBE 或手动替换 data/.env。
          </Description>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              isDisabled={rotateEncryption.isPending}
              onPress={() => setPending('rotate')}
            >
              {rotateEncryption.isPending ? <Spinner size="sm" /> : null}
              {rotateEncryption.isPending ? '轮换中…' : '轮换加密密钥'}
            </Button>
          </div>
        </Card.Content>
      </Card>

      {/* 服务控制 */}
      <Card className="border-danger/20">
        <Card.Header className="flex-row items-center gap-3">
          <SectionIcon tone="danger">
            <Power className="size-4.5" aria-hidden />
          </SectionIcon>
          <div>
            <Card.Title className="text-danger">服务控制</Card.Title>
            <Card.Description>
              重启会拉起新进程；停止后控制台将失联
            </Card.Description>
          </div>
        </Card.Header>
        <Card.Content>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              isDisabled={restartService.isPending || recovering === 'restart'}
              onPress={() => setPending('restart')}
            >
              {restartService.isPending || recovering === 'restart' ? (
                <Spinner size="sm" />
              ) : null}
              {restartService.isPending || recovering === 'restart'
                ? '重启中…'
                : '重启服务'}
            </Button>
            <Button
              variant="danger"
              isDisabled={stopService.isPending || recovering === 'stop'}
              onPress={() => setPending('stop')}
            >
              {stopService.isPending || recovering === 'stop' ? (
                <Spinner size="sm" />
              ) : null}
              {stopService.isPending || recovering === 'stop'
                ? '停止中…'
                : '停止服务'}
            </Button>
          </div>
        </Card.Content>
      </Card>

      <SetPasswordDialog
        open={passwordDialog}
        onOpenChange={setPasswordDialog}
        forceRemote={remoteWarning && !passwordSet}
        onSuccess={() => {
          setPasswordSet(true);
          if (remoteWarning) {
            void saveNetwork();
          }
        }}
      />

      <ConfirmDialog
        open={pending === 'rotate'}
        onOpenChange={(open) => !open && setPending(null)}
        title="轮换加密密钥"
        description="将提升密钥版本并重新加密本地凭据。请确认已备份当前密钥。"
        confirmLabel="继续轮换"
        loading={rotateEncryption.isPending}
        status="warning"
        onConfirm={() => void handleRotate()}
      />
      <ConfirmDialog
        open={pending === 'restart'}
        onOpenChange={(open) => !open && setPending(null)}
        title="重启服务"
        description="将停止当前进程并尝试拉起新进程。确认继续？"
        confirmLabel="重启"
        loading={restartService.isPending}
        status="warning"
        onConfirm={() => void handleRestart()}
      />
      <ConfirmDialog
        open={pending === 'stop'}
        onOpenChange={(open) => !open && setPending(null)}
        title="停止服务"
        description="停止后自动登录不可用，控制台也会失联。确认停止？"
        confirmLabel="停止"
        loading={stopService.isPending}
        status="danger"
        onConfirm={() => void handleStop()}
      />
    </div>
  );
}
