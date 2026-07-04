import { useState, useEffect } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { 
  Button, TextField, Label, Input, Switch, Card, Skeleton
} from '@heroui/react';
import { useSettings, useUpdateSettings, useClearCache } from '../lib/api/hooks';

const queryClient = new QueryClient();

export function SettingsIsland() {
  return (
    <QueryClientProvider client={queryClient}>
      <SettingsInner />
    </QueryClientProvider>
  );
}

function SettingsCard({ title, icon, children }: { title: string; icon: React.ReactNode; children: React.ReactNode }) {
  return (
    <Card>
      <Card.Header className="gap-3">
        <div className="w-8 h-8 rounded-lg bg-muted flex items-center justify-center">
          {icon}
        </div>
        <Card.Title>{title}</Card.Title>
      </Card.Header>
      <Card.Content>
        {children}
      </Card.Content>
    </Card>
  );
}

function SettingsRow({ label, description, children }: { label: string; description: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between py-2">
      <div className="mr-4">
        <div className="text-sm font-medium text-foreground">{label}</div>
        <div className="text-xs text-muted-foreground mt-0.5">{description}</div>
      </div>
      {children}
    </div>
  );
}

function SettingsInner() {
  const { data, isLoading } = useSettings();
  const updateSettings = useUpdateSettings();
  const clearCache = useClearCache();

  const [port, setPort] = useState('');
  const [webuiPort, setWebuiPort] = useState('');
  const [autostart, setAutostart] = useState(true);
  const [autorestart, setAutorestart] = useState(true);
  const [eventlog, setEventlog] = useState(true);
  const [pwdlock, setPwdlock] = useState(false);

  useEffect(() => {
    if (data?.data) {
      setPort(String(data.data.Global.port));
      setWebuiPort(String(data.data.Global.webui_port));
    }
  }, [data]);

  const handleSave = async () => {
    await updateSettings.mutateAsync({
      Global: { port: parseInt(port), webui_port: parseInt(webuiPort) }
    });
  };

  const handleClearCache = async () => {
    if (confirm('确定要清除缓存吗？')) {
      await clearCache.mutateAsync();
      alert('缓存已清除');
    }
  };

  if (isLoading) {
    return (
      <>
        <div className="page-header">
          <h1 className="page-title">设置</h1>
        </div>
        <div className="page-content">
          <div className="flex flex-col gap-4 max-w-2xl">
            {[...Array(3)].map((_, i) => (
              <Card key={i}>
                <Card.Content>
                  <Skeleton className="w-24 h-4 rounded mb-4" />
                  <Skeleton className="w-full h-11 rounded-lg mb-3" />
                  <Skeleton className="w-full h-11 rounded-lg" />
                </Card.Content>
              </Card>
            ))}
          </div>
        </div>
      </>
    );
  }

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">设置</h1>
        <p className="page-subtitle">配置服务参数</p>
      </div>

      <div className="page-content">
        <div className="flex flex-col gap-4 max-w-2xl">
          {/* General */}
          <SettingsCard 
            title="常规设置" 
            icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-secondary-foreground"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>}
          >
            <SettingsRow label="开机自启" description="系统启动时自动运行服务">
              <Switch isSelected={autostart} onChange={setAutostart}>
                <Switch.Content>
                  <Switch.Control><Switch.Thumb /></Switch.Control>
                </Switch.Content>
              </Switch>
            </SettingsRow>
            <SettingsRow label="自动重启" description="服务异常退出时自动重启">
              <Switch isSelected={autorestart} onChange={setAutorestart}>
                <Switch.Content>
                  <Switch.Control><Switch.Thumb /></Switch.Control>
                </Switch.Content>
              </Switch>
            </SettingsRow>
          </SettingsCard>

          {/* Service */}
          <SettingsCard 
            title="服务设置" 
            icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-secondary-foreground"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"/><rect x="2" y="14" width="20" height="8" rx="2" ry="2"/><line x1="6" y1="6" x2="6.01" y2="6"/><line x1="6" y1="18" x2="6.01" y2="18"/></svg>}
          >
            <div className="grid grid-cols-2 gap-4">
              <TextField>
                <Label>API 监听地址</Label>
                <Input value="127.0.0.1" isReadOnly />
              </TextField>
              <TextField>
                <Label>端口</Label>
                <Input type="number" value={port} onChange={setPort} placeholder="24300" />
              </TextField>
            </div>
            <div className="grid grid-cols-2 gap-4 mt-4">
              <TextField>
                <Label>WebUI 端口</Label>
                <Input type="number" value={webuiPort} onChange={setWebuiPort} placeholder="3000" />
              </TextField>
            </div>
          </SettingsCard>

          {/* Advanced */}
          <SettingsCard 
            title="高级" 
            icon={<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="text-secondary-foreground"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>}
          >
            <SettingsRow label="启用 Windows 事件日志" description="将错误日志写入 Windows 事件查看器">
              <Switch isSelected={eventlog} onChange={setEventlog}>
                <Switch.Content>
                  <Switch.Control><Switch.Thumb /></Switch.Control>
                </Switch.Content>
              </Switch>
            </SettingsRow>
            <SettingsRow label="密码错误禁用" description="多次密码错误后临时禁用该账户">
              <Switch isSelected={pwdlock} onChange={setPwdlock}>
                <Switch.Content>
                  <Switch.Control><Switch.Thumb /></Switch.Control>
                </Switch.Content>
              </Switch>
            </SettingsRow>
          </SettingsCard>

          {/* Danger Zone */}
          <div className="bg-danger/10 border border-danger/20 rounded-lg px-5 py-4 flex items-center justify-between">
            <div>
              <div className="text-sm font-medium text-danger">清除缓存</div>
              <div className="text-xs text-muted-foreground mt-0.5">清除所有缓存数据，服务可能短暂中断</div>
            </div>
            <Button variant="danger" size="sm" onPress={handleClearCache}>
              清除缓存
            </Button>
          </div>

          {/* Save - auto saved */}
        </div>
      </div>
    </>
  );
}
