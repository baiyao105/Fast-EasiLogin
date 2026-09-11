import { Chip } from '@heroui/react';

const STATUS_MAP: Record<
  string,
  {
    label: string;
    color: 'success' | 'warning' | 'danger' | 'default' | 'accent';
  }
> = {
  running: { label: '运行中', color: 'success' },
  stopped: { label: '已停止', color: 'danger' },
  restarting: { label: '重启中', color: 'warning' },
  paused: { label: '已暂停', color: 'warning' },
  disconnected: { label: '连接中断', color: 'danger' },
  success: { label: '成功', color: 'success' },
  invalid_credentials: { label: '凭据无效', color: 'danger' },
  disabled: { label: '账号禁用', color: 'warning' },
  upstream: { label: '上游异常', color: 'warning' },
  system: { label: '系统错误', color: 'danger' },
};

export function StatusPill({
  status,
  className,
}: {
  status: string | number;
  className?: string;
}) {
  const raw = String(status);
  // 后端 controller.status() 可能返回 HTTP 风格状态码
  const key = raw === '200' || raw === 'ok' ? 'running' : raw;
  const mapped = STATUS_MAP[key] ?? {
    label: raw,
    color: 'default' as const,
  };
  return (
    <Chip color={mapped.color} className={className}>
      {mapped.label}
    </Chip>
  );
}
