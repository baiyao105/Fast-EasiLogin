import { useState } from 'react';
import { Card, Chip, Skeleton } from '@heroui/react';
import { useWebSocket } from '../lib/api/websocket';
import { formatDistanceToNow } from '../lib/utils/time';
import { LoginDialog } from '../components/business/login-dialog';

interface LoginRecord {
  username: string;
  login_time: string;
  ip_address: string;
  status: string;
  head_img?: string;
}

export function RecentLoginsIsland() {
  const [logins, setLogins] = useState<LoginRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedLogin, setSelectedLogin] = useState<LoginRecord | null>(null);

  useWebSocket({
    onRecentLogins: (data) => {
      setLogins(data);
      setIsLoading(false);
    },
  });

  if (isLoading) {
    return (
      <Card>
        <Card.Header>
          <Card.Title>最近登录</Card.Title>
        </Card.Header>
        <Card.Content>
          <div className="flex flex-col gap-3">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="flex items-center gap-3">
                <Skeleton className="w-10 h-10 rounded-full" />
                <div className="flex-1">
                  <Skeleton className="w-20 h-3.5 rounded mb-2" />
                  <Skeleton className="w-16 h-3 rounded" />
                </div>
              </div>
            ))}
          </div>
        </Card.Content>
      </Card>
    );
  }

  if (logins.length === 0) {
    return (
      <Card>
        <Card.Header>
          <Card.Title>最近登录</Card.Title>
        </Card.Header>
        <Card.Content>
          <div className="py-6 text-center">
            <div className="w-10 h-10 rounded-full bg-muted flex items-center justify-center mx-auto mb-2">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-muted-foreground">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                <circle cx="12" cy="7" r="4" />
              </svg>
            </div>
            <div className="text-sm text-muted-foreground">暂无登录记录</div>
          </div>
        </Card.Content>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <Card.Header className="justify-between">
          <Card.Title>最近登录</Card.Title>
          <span className="text-xs text-muted-foreground">最近 20 条</span>
        </Card.Header>
        <Card.Content className="p-0">
          <div className="max-h-72 overflow-y-auto">
            {logins.slice(0, 20).map((login, index) => (
              <div
                key={`${login.username}-${login.login_time}-${index}`}
                onClick={() => setSelectedLogin(login)}
                className="flex items-center gap-3 px-4 py-3 rounded-lg transition-all duration-200 cursor-pointer hover:bg-muted/50"
              >
                <div className="w-10 h-10 rounded-full bg-accent/10 text-accent flex items-center justify-center text-sm font-semibold flex-shrink-0 overflow-hidden">
                  {login.head_img ? (
                    <img src={login.head_img} alt={login.username} className="w-full h-full object-cover" />
                  ) : (
                    login.username.charAt(0).toUpperCase()
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-foreground">{login.username}</span>
                    <Chip
                      color={login.status === 'success' ? 'success' : 'danger'}
                      variant="soft"
                      size="sm"
                    >
                      {login.status === 'success' ? '成功' : '失败'}
                    </Chip>
                  </div>
                  <div className="text-xs text-muted-foreground font-mono mt-0.5">
                    {login.ip_address}
                  </div>
                </div>
                <span className="text-xs text-muted-foreground whitespace-nowrap">
                  {formatDistanceToNow(login.login_time)}
                </span>
              </div>
            ))}
          </div>
        </Card.Content>
      </Card>

      <LoginDialog
        login={selectedLogin}
        isOpen={!!selectedLogin}
        onClose={() => setSelectedLogin(null)}
      />
    </>
  );
}
