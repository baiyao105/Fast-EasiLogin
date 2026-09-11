import { PersonPlus } from '@gravity-ui/icons';
import {
  Button,
  Description,
  FieldError,
  Form,
  Input,
  Label,
  Modal,
  TextField,
  toast,
} from '@heroui/react';
import { useEffect, useState } from 'react';
import { AccountDetailModal } from '@/components/account-detail';
import { useCreateAccount } from '@/hooks/use-dashboard';
import { api } from '@/lib/api';
import type { AccountVerification } from '@/lib/types';

const PHONE_PATTERN = /^1[3-9]\d{9}$/;

function isValidPhone(value: string): boolean {
  return PHONE_PATTERN.test(value.trim());
}

export function AddAccountDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [phoneError, setPhoneError] = useState<string | null>(null);
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [formError, setFormError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [verification, setVerification] = useState<AccountVerification | null>(
    null,
  );
  const [loadingToastId, setLoadingToastId] = useState<string | null>(null);
  const createAccount = useCreateAccount();

  useEffect(() => {
    if (!open) {
      setPhone('');
      setPassword('');
      setPhoneError(null);
      setPasswordError(null);
      setFormError(null);
      setPending(false);
      setConfirmOpen(false);
      setVerification(null);
      if (loadingToastId) {
        toast.close(loadingToastId);
        setLoadingToastId(null);
      }
    }
  }, [loadingToastId, open]);

  function validate(): boolean {
    let ok = true;
    if (!phone.trim()) {
      setPhoneError('请输入手机号');
      ok = false;
    } else if (!isValidPhone(phone)) {
      setPhoneError('请输入有效的 11 位手机号');
      ok = false;
    } else {
      setPhoneError(null);
    }

    if (!password) {
      setPasswordError('请输入账号密码');
      ok = false;
    } else {
      setPasswordError(null);
    }

    return ok;
  }

  async function handleSubmit(event?: { preventDefault?: () => void }) {
    event?.preventDefault?.();
    setFormError(null);
    if (!validate()) {
      return;
    }

    setPending(true);
    const loadingId = toast('验证中...', {
      description: '请稍后, 正在检查您的账户是否正确',
      isLoading: true,
      timeout: 0,
    });
    setLoadingToastId(loadingId);

    try {
      const result = await api.verifyAccount(phone.trim(), password);
      setVerification(result);
      setConfirmOpen(true);
      // loading toast 保持到用户确认/取消
    } catch (err) {
      const message = err instanceof Error ? err.message : '未知错误';
      toast.close(loadingId);
      setLoadingToastId(null);
      toast.danger(`验证失败 ${message}`);
      setFormError(message);
    } finally {
      setPending(false);
    }
  }

  function closeLoadingToast() {
    if (loadingToastId) {
      toast.close(loadingToastId);
      setLoadingToastId(null);
    }
  }

  async function handleConfirmAdd() {
    if (!verification) {
      return;
    }
    try {
      await createAccount.mutateAsync(verification.verification_token);
      const name =
        verification.profile.nickname ||
        verification.profile.real_name ||
        verification.profile.user_id;
      closeLoadingToast();
      toast.success(`验证成功, ${name}!`);
      setConfirmOpen(false);
      onOpenChange(false);
    } catch (err) {
      const message = err instanceof Error ? err.message : '添加失败';
      closeLoadingToast();
      toast.danger(`验证失败 ${message}`);
      setFormError(message);
      setConfirmOpen(false);
    }
  }

  function handleCancelAdd() {
    closeLoadingToast();
    toast.warning('您取消了账号添加');
    setConfirmOpen(false);
    setVerification(null);
  }

  return (
    <>
      <Modal isOpen={open && !confirmOpen} onOpenChange={onOpenChange}>
        <Modal.Backdrop isDismissable={false}>
          <Modal.Container placement="center" size="md">
            <Modal.Dialog>
              <Modal.CloseTrigger />
              <Modal.Header>
                <Modal.Icon className="rounded-xl bg-accent/15 p-2 text-accent">
                  <PersonPlus className="size-5" aria-hidden />
                </Modal.Icon>
                <Modal.Heading>添加账号</Modal.Heading>
              </Modal.Header>
              <Modal.Body>
                <Form
                  className="space-y-5"
                  onSubmit={(event) => {
                    void handleSubmit(event);
                  }}
                >
                  <TextField
                    className="w-full"
                    isInvalid={Boolean(phoneError)}
                    isRequired
                  >
                    <Label>手机号</Label>
                    <Input
                      type="tel"
                      inputMode="numeric"
                      autoComplete="username"
                      placeholder="请输入 Seewo 账号手机号"
                      value={phone}
                      onChange={(event) => {
                        setPhone(event.target.value);
                        if (phoneError) {
                          setPhoneError(null);
                        }
                      }}
                      variant="secondary"
                    />
                    <Description>用于登录 Seewo，仅本机验证使用</Description>
                    <FieldError>{phoneError}</FieldError>
                  </TextField>

                  <TextField
                    className="w-full"
                    isInvalid={Boolean(passwordError)}
                    isRequired
                  >
                    <Label>账号密码</Label>
                    <Input
                      type="password"
                      autoComplete="current-password"
                      placeholder="请输入账号密码"
                      value={password}
                      onChange={(event) => {
                        setPassword(event.target.value);
                        if (passwordError) {
                          setPasswordError(null);
                        }
                      }}
                      variant="secondary"
                    />
                    <Description>密码将保存在本地存储中保护</Description>
                    <FieldError>{passwordError}</FieldError>
                  </TextField>

                  {formError ? (
                    <p role="alert" className="text-sm text-danger">
                      {formError}
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
                      {pending ? '验证中...' : '提交'}
                    </Button>
                  </div>
                </Form>
              </Modal.Body>
            </Modal.Dialog>
          </Modal.Container>
        </Modal.Backdrop>
      </Modal>

      <AccountDetailModal
        open={confirmOpen && Boolean(verification)}
        onOpenChange={(next) => {
          if (!next) {
            handleCancelAdd();
          }
        }}
        title="这是否为您的账号？"
        showPhone
        showTimestamps={false}
        profile={
          verification
            ? {
                user_id: verification.profile.user_id,
                phone: verification.profile.phone,
                nickname: verification.profile.nickname,
                real_name: verification.profile.real_name,
                avatar_url: verification.profile.avatar_url,
                school: verification.profile.school,
                stage_name: verification.profile.stage_name,
                subject_name: verification.profile.subject_name,
              }
            : null
        }
        confirmLabel="确认添加"
        cancelLabel="不是，取消"
        loading={createAccount.isPending}
        onConfirm={() => void handleConfirmAdd()}
      />
    </>
  );
}
