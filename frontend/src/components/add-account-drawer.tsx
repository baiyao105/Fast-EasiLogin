import { Button, Drawer, Input, Label, TextField, toast } from '@heroui/react';
import { useEffect, useState } from 'react';
import { useCreateAccount } from '@/hooks/use-dashboard';
import { api } from '@/lib/api';
import type { AccountVerification } from '@/lib/types';
import { formatDateTime } from '@/lib/utils';

export function AddAccountDrawer({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [account, setAccount] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [verification, setVerification] = useState<AccountVerification | null>(
    null,
  );
  const createAccount = useCreateAccount();

  useEffect(() => {
    if (!open) {
      setAccount('');
      setPassword('');
      setError(null);
      setVerifying(false);
      setVerification(null);
    }
  }, [open]);

  async function handleVerify() {
    setError(null);
    if (!account.trim() || !password) {
      setError('请填写账号与密码');
      return;
    }
    setVerifying(true);
    try {
      const result = await api.verifyAccount(account.trim(), password);
      setVerification(result);
      setPassword('');
      toast.success('凭证验证成功，请确认资料后保存');
    } catch (err) {
      const message = err instanceof Error ? err.message : '验证失败';
      setError(message);
      toast.danger(message);
    } finally {
      setVerifying(false);
    }
  }

  async function handleSave() {
    if (!verification) {
      return;
    }
    try {
      await createAccount.mutateAsync(verification.verification_token);
      toast.success('账号已添加');
      onOpenChange(false);
    } catch (err) {
      const message = err instanceof Error ? err.message : '保存失败';
      setError(message);
      toast.danger(message);
    }
  }

  return (
    <Drawer isOpen={open} onOpenChange={onOpenChange}>
      <Drawer.Backdrop isDismissable={false}>
        <Drawer.Content placement="right">
          <Drawer.Dialog>
            <Drawer.Handle />
            <Drawer.CloseTrigger />
            <Drawer.Header>
              <Drawer.Heading>添加账号</Drawer.Heading>
            </Drawer.Header>
            <Drawer.Body className="space-y-5">
              {!verification ? (
                <>
                  <p className="text-sm leading-6 text-neutral-600">
                    先验证 Seewo 凭据。验证通过后只保存一次性
                    token，浏览器不会保留密码。
                  </p>
                  <TextField className="w-full">
                    <Label>账号</Label>
                    <Input
                      value={account}
                      onChange={(event) => setAccount(event.target.value)}
                      autoComplete="username"
                      placeholder="手机号或用户 ID"
                      variant="secondary"
                    />
                  </TextField>
                  <TextField className="w-full">
                    <Label>密码</Label>
                    <Input
                      type="password"
                      value={password}
                      onChange={(event) => setPassword(event.target.value)}
                      autoComplete="current-password"
                      placeholder="仅用于本次验证"
                      variant="secondary"
                    />
                  </TextField>
                  {error ? (
                    <p role="alert" className="text-sm text-red-600">
                      {error}
                    </p>
                  ) : null}
                </>
              ) : (
                <div className="space-y-4 rounded-2xl border border-emerald-100 bg-emerald-50/60 p-4">
                  <div className="text-sm font-medium text-emerald-800">
                    验证成功
                  </div>
                  <div className="space-y-2 text-sm text-neutral-700">
                    <div className="flex justify-between gap-3">
                      <span>昵称</span>
                      <span className="font-medium">
                        {verification.profile.nickname || '—'}
                      </span>
                    </div>
                    <div className="flex justify-between gap-3">
                      <span>用户 ID</span>
                      <span className="font-medium">
                        {verification.profile.user_id}
                      </span>
                    </div>
                    <div className="flex justify-between gap-3">
                      <span>手机号</span>
                      <span className="font-medium">
                        {verification.profile.phone || '—'}
                      </span>
                    </div>
                    <div className="flex justify-between gap-3">
                      <span>Token 有效期</span>
                      <span className="font-medium">
                        {formatDateTime(verification.expires_at)}
                      </span>
                    </div>
                  </div>
                  {error ? (
                    <p role="alert" className="text-sm text-red-600">
                      {error}
                    </p>
                  ) : null}
                </div>
              )}
            </Drawer.Body>
            <Drawer.Footer className="flex justify-end gap-2">
              <Button variant="secondary" onPress={() => onOpenChange(false)}>
                取消
              </Button>
              {!verification ? (
                <Button isDisabled={verifying} onPress={handleVerify}>
                  {verifying ? '验证中…' : '验证凭证'}
                </Button>
              ) : (
                <Button
                  isDisabled={createAccount.isPending}
                  onPress={handleSave}
                >
                  {createAccount.isPending ? '保存中…' : '保存账号'}
                </Button>
              )}
            </Drawer.Footer>
          </Drawer.Dialog>
        </Drawer.Content>
      </Drawer.Backdrop>
    </Drawer>
  );
}
