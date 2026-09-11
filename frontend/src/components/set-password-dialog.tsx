import {
  Button,
  Description,
  Form,
  Input,
  Label,
  Modal,
  TextField,
  toast,
} from '@heroui/react';
import { useState } from 'react';
import { api } from '@/lib/api';

export function SetPasswordDialog({
  open,
  onOpenChange,
  onSuccess,
  forceRemote,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSuccess?: () => void;
  forceRemote?: boolean;
}) {
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function handleSubmit(e?: { preventDefault?: () => void }) {
    e?.preventDefault?.();
    setError(null);
    if (password.length < 6) {
      setError('密码至少 6 位');
      return;
    }
    if (password !== confirm) {
      setError('两次输入不一致');
      return;
    }
    setPending(true);
    try {
      await api.changeDashboardPassword(password);
      toast.success('控制台密码已设置');
      setPassword('');
      setConfirm('');
      onOpenChange(false);
      onSuccess?.();
    } catch (err) {
      const msg = err instanceof Error ? err.message : '设置失败';
      setError(msg);
      toast.danger(msg);
    } finally {
      setPending(false);
    }
  }

  return (
    <Modal isOpen={open} onOpenChange={onOpenChange}>
      <Modal.Backdrop isDismissable={false}>
        <Modal.Container placement="center" size="md">
          <Modal.Dialog>
            <Modal.CloseTrigger />
            <Modal.Header>
              <Modal.Heading>设定控制台密码</Modal.Heading>
            </Modal.Header>
            <Modal.Body>
              <Form
                className="space-y-4"
                onSubmit={(e) => void handleSubmit(e)}
              >
                {forceRemote ? (
                  <Description className="text-sm text-warning">
                    控制台将对外可访问，必须设置密码后才能保存网络配置。
                  </Description>
                ) : null}
                <TextField
                  className="w-full"
                  isInvalid={Boolean(error)}
                  isRequired
                >
                  <Label>新密码</Label>
                  <Input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="new-password"
                    variant="secondary"
                    placeholder="至少 6 位"
                  />
                  <Description>访问 WebUI 时需要输入此密码</Description>
                </TextField>
                <TextField
                  className="w-full"
                  isInvalid={Boolean(error)}
                  isRequired
                >
                  <Label>确认密码</Label>
                  <Input
                    type="password"
                    value={confirm}
                    onChange={(e) => setConfirm(e.target.value)}
                    autoComplete="new-password"
                    variant="secondary"
                  />
                </TextField>
                {error ? (
                  <p role="alert" className="text-sm text-danger">
                    {error}
                  </p>
                ) : null}
                <div className="flex justify-end gap-2 pt-1">
                  <Button
                    type="button"
                    variant="secondary"
                    isDisabled={pending}
                    onPress={() => onOpenChange(false)}
                  >
                    取消
                  </Button>
                  <Button type="submit" isDisabled={pending}>
                    {pending ? '设置中…' : '设定密码'}
                  </Button>
                </div>
              </Form>
            </Modal.Body>
          </Modal.Dialog>
        </Modal.Container>
      </Modal.Backdrop>
    </Modal>
  );
}
