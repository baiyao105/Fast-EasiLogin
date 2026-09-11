import { CircleCheck, Sparkles } from '@gravity-ui/icons';
import {
  Button,
  Description,
  ErrorMessage,
  InputGroup,
  Label,
  Modal,
  Spinner,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  toast,
} from '@heroui/react';
import { useEffect, useState } from 'react';
import { useSetupEncryption } from '@/hooks/use-dashboard';
import { api } from '@/lib/api';

type KeySource = 'environment' | 'dpapi';
type Step = 'welcome' | 'key' | 'done';
type ValidState = 'idle' | 'loading' | 'ok' | 'error';

export function OobeModal({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [step, setStep] = useState<Step>('welcome');
  const [key, setKey] = useState('');
  const [keySource, setKeySource] = useState<KeySource>('environment');
  const [valid, setValid] = useState<ValidState>('idle');
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const setup = useSetupEncryption();

  // 打开时重置状态并预览密钥
  useEffect(() => {
    if (!open) {
      setStep('welcome');
      setValid('idle');
      setErrorMsg(null);
      return;
    }
    let cancelled = false;
    void api
      .listKeyPreview()
      .then((k) => {
        if (!cancelled && k) setKey(k);
      })
      .catch(() => null);
    return () => {
      cancelled = true;
    };
  }, [open]);

  async function handleGenerate() {
    try {
      const k = await api.listKeyPreview();
      if (k) setKey(k);
    } catch {
      // ignore
    }
  }

  async function handleValidateAndSave() {
    setValid('loading');
    setErrorMsg(null);
    try {
      await setup.mutateAsync({
        mode: 'custom',
        key_source: keySource,
        custom_key: key.trim(),
      });
      setValid('ok');
      window.setTimeout(() => setStep('done'), 2000);
    } catch (err) {
      setValid('error');
      setErrorMsg(
        err instanceof Error
          ? err.message
          : '验证失败，请检查密钥格式或存储方式',
      );
    }
  }

  const validating = valid === 'loading' || valid === 'ok';

  return (
    <Modal isOpen={open} onOpenChange={onOpenChange}>
      <Modal.Backdrop isDismissable={false} variant="blur">
        <Modal.Container placement="center" size="md">
          <Modal.Dialog className="overflow-hidden">
            <Modal.Body className="relative min-h-[420px] p-8">
              {step === 'welcome' ? (
                <div
                  key="welcome"
                  className="oobe-fade-in flex h-full min-h-[360px] flex-col items-center justify-center gap-4 text-center"
                >
                  <img
                    src="/logo.png"
                    alt="FastLogin"
                    className="size-16 rounded-2xl object-contain"
                  />
                  <h1 className="text-3xl font-bold tracking-tight">
                    FastLogin
                  </h1>
                  <p className="text-sm text-muted">
                    本地快速登录控制台 · 首次使用向导
                  </p>
                  <Button className="mt-4" onPress={() => setStep('key')}>
                    下一步
                  </Button>
                </div>
              ) : null}

              {step === 'key' ? (
                <div key="key" className="oobe-fade-in space-y-6">
                  <div className="text-lg font-semibold">密钥设置</div>

                  <TextField className="w-full" isRequired>
                    <Label>加密密钥</Label>
                    <InputGroup>
                      <InputGroup.Input
                        value={key}
                        onChange={(e) => setKey(e.target.value)}
                        className="font-mono text-xs"
                        disabled={validating}
                      />
                      <InputGroup.Suffix>
                        <Button
                          size="sm"
                          variant="ghost"
                          isIconOnly
                          isDisabled={validating}
                          aria-label="自动生成密钥"
                          onPress={() => void handleGenerate()}
                        >
                          <Sparkles className="size-4" aria-hidden />
                        </Button>
                      </InputGroup.Suffix>
                    </InputGroup>
                    <Description>
                      URL-safe base64，32
                      字节。点击右侧图标可自动生成，也可手动粘贴。
                    </Description>
                    {errorMsg && valid === 'error' ? (
                      <ErrorMessage>{errorMsg}</ErrorMessage>
                    ) : null}
                  </TextField>

                  <div>
                    <div className="mb-2 text-sm font-medium">密钥存储方式</div>
                    <ToggleButtonGroup
                      selectionMode="single"
                      disallowEmptySelection
                      selectedKeys={[keySource]}
                      onSelectionChange={(keys) => {
                        const v = Array.from(keys)[0];
                        if (v === 'environment' || v === 'dpapi')
                          setKeySource(v);
                      }}
                      className="w-full"
                      isDisabled={validating}
                    >
                      <ToggleButton id="environment" className="flex-1">
                        环境变量文件
                      </ToggleButton>
                      <ToggleButton id="dpapi" className="flex-1">
                        Windows DPAPI
                      </ToggleButton>
                    </ToggleButtonGroup>
                    <Description className="mt-2">
                      {keySource === 'environment'
                        ? '写入 data/.env，便于备份与迁移。'
                        : 'DPAPI 加密后写入 data/.env，绑定当前 Windows 用户。'}
                    </Description>
                    {errorMsg && keySource === 'dpapi' ? (
                      <ErrorMessage className="mt-1">{errorMsg}</ErrorMessage>
                    ) : null}
                  </div>

                  <div className="flex justify-end">
                    <Button
                      isDisabled={!key.trim() || validating}
                      onPress={() => void handleValidateAndSave()}
                    >
                      {validating ? '验证中…' : '下一步'}
                    </Button>
                  </div>
                </div>
              ) : null}

              {validating ? (
                <div className="oobe-fade-in absolute inset-0 z-10 flex flex-col items-center justify-center gap-4 bg-background/92 backdrop-blur-sm">
                  {valid === 'loading' ? (
                    <>
                      <Spinner size="lg" />
                      <p className="text-sm text-muted">
                        请稍后，我们正在验证字段是否正确
                      </p>
                    </>
                  ) : (
                    <>
                      <CircleCheck
                        className="size-12 text-success"
                        aria-hidden
                      />
                      <p className="text-sm font-medium text-success">正确！</p>
                    </>
                  )}
                </div>
              ) : null}

              {step === 'done' ? (
                <div
                  key="done"
                  className="oobe-fade-in flex h-full min-h-[360px] flex-col items-center justify-center gap-4 text-center"
                >
                  <div className="app-brand-mark size-16 rounded-2xl bg-success/15 text-success">
                    <CircleCheck className="size-8" aria-hidden />
                  </div>
                  <h1 className="text-3xl font-bold tracking-tight">
                    大功告成！
                  </h1>
                  <p className="text-sm text-muted">
                    初始化完成，可以开始添加账号了
                  </p>
                  <Button
                    className="mt-4"
                    onPress={() => {
                      toast.success('欢迎使用 FastLogin');
                      onOpenChange(false);
                    }}
                  >
                    开始使用
                  </Button>
                </div>
              ) : null}
            </Modal.Body>
          </Modal.Dialog>
        </Modal.Container>
      </Modal.Backdrop>
    </Modal>
  );
}
