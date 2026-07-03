import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState, useEffect } from 'react';
import { useSettings, useUpdateSettings, useClearCache } from '../lib/api/hooks';

const queryClient = new QueryClient();

export function SettingsIsland() {
  return (
    <QueryClientProvider client={queryClient}>
      <SettingsInner />
    </QueryClientProvider>
  );
}

function SettingsInner() {
  const { data, isLoading } = useSettings();
  const updateSettings = useUpdateSettings();
  const clearCache = useClearCache();

  const [port, setPort] = useState('');
  const [webuiPort, setWebuiPort] = useState('');

  useEffect(() => {
    if (data?.data) {
      setPort(String(data.data.Global.port));
      setWebuiPort(String(data.data.Global.webui_port));
    }
  }, [data]);

  const handleSave = async () => {
    await updateSettings.mutateAsync({
      Global: {
        port: parseInt(port),
        webui_port: parseInt(webuiPort)
      }
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
        <div className="page-container">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {[...Array(2)].map((_, i) => (
              <div key={i} className="card">
                <div className="card-content" style={{ opacity: 0.5 }}>
                  <div style={{ height: 16, width: 80, background: 'var(--bg-surface-hover)', borderRadius: 4, marginBottom: 16 }} />
                  <div style={{ height: 36, background: 'var(--bg-surface-hover)', borderRadius: 4, marginBottom: 12 }} />
                  <div style={{ height: 36, background: 'var(--bg-surface-hover)', borderRadius: 4 }} />
                </div>
              </div>
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
      </div>

      <div className="page-container">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div className="card">
            <div className="card-header">
              <h2 className="card-title">服务配置</h2>
            </div>
            <div className="card-content">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16, maxWidth: 320 }}>
                <div>
                  <label className="label">API 端口</label>
                  <input
                    type="number"
                    className="input"
                    value={port}
                    onChange={(e) => setPort(e.target.value)}
                    placeholder="24300"
                  />
                </div>

                <div>
                  <label className="label">WebUI 端口</label>
                  <input
                    type="number"
                    className="input"
                    value={webuiPort}
                    onChange={(e) => setWebuiPort(e.target.value)}
                    placeholder="3000"
                  />
                </div>

                <div style={{ display: 'flex', justifyContent: 'flex-end', paddingTop: 8 }}>
                  <button className="btn btn-primary" onClick={handleSave}>
                    保存设置
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-header">
              <h2 className="card-title">缓存管理</h2>
            </div>
            <div className="card-content">
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-primary)' }}>
                    清除所有缓存数据
                  </div>
                  <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 2 }}>
                    这将清除所有登录缓存和用户信息缓存
                  </div>
                </div>
                <button className="btn btn-secondary" onClick={handleClearCache}>
                  清除缓存
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}
