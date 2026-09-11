import { Button, Input, Label, Surface, TextField, toast } from '@heroui/react';
import { useState } from 'react';
import { useLogin } from '@/hooks/use-dashboard';

export function SignInGate({ onComplete }: { onComplete: () => void }) {
  const login = useLogin();
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit() {
    setError(null);
    if (!password) {
      setError('请输入控制台密码');
      return;
    }
    try {
      await login.mutateAsync(password);
      toast.success('已登录');
      setPassword('');
      onComplete();
    } catch (err) {
      const message = err instanceof Error ? err.message : '登录失败';
      setError(message);
      toast.danger(message);
    }
  }

  return (
    <div className="flex min-h-dvh items-center justify-center bg-background p-6">
      <Surface className="page-enter w-full max-w-md rounded-2xl border border-separator p-8">
        <div className="mb-7 flex items-center gap-2">
          <img
            src="/logo.png"
            alt="FastLogin"
            className="size-8 rounded-lg object-contain"
          />
          <div>
            <div className="text-base font-bold">FastLogin</div>
            <div className="text-sm text-muted">Seewo 本地控制台</div>
          </div>
        </div>

        <p className="mb-5 text-sm leading-6 text-muted">
          输入控制台密码以继续管理账号、登录活动与服务设置。
        </p>

        <div className="space-y-4">
          <TextField className="w-full">
            <Label>控制台密码</Label>
            <Input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') {
                  void handleSubmit();
                }
              }}
              autoComplete="current-password"
              autoFocus
              variant="secondary"
            />
          </TextField>
          {error ? (
            <p role="alert" className="text-sm text-danger">
              {error}
            </p>
          ) : null}
          <Button
            fullWidth
            isDisabled={login.isPending}
            onPress={() => void handleSubmit()}
          >
            {login.isPending ? '登录中…' : '进入控制台'}
          </Button>
        </div>
      </Surface>
    </div>
  );
}
