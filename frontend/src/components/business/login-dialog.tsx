import { Modal } from '@heroui/react';

interface LoginRecord {
  username: string;
  login_time: string;
  ip_address: string;
  status: string;
  head_img?: string;
}

interface LoginDialogProps {
  login: LoginRecord | null;
  isOpen: boolean;
  onClose: () => void;
}

function formatTime(timeStr: string): string {
  try {
    const date = new Date(timeStr);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    });
  } catch {
    return timeStr;
  }
}

export function LoginDialog({ login, isOpen, onClose }: LoginDialogProps) {
  if (!login) return null;

  const isSuccess = login.status === 'success';

  return (
    <Modal isOpen={isOpen} onOpenChange={onClose}>
      <Modal.Backdrop>
        <Modal.Container placement="center" size="sm">
          <Modal.Dialog>
            <Modal.CloseTrigger />
            <Modal.Header>
              <Modal.Heading>登录详情</Modal.Heading>
            </Modal.Header>
            <Modal.Body>
              <div className="flex flex-col gap-4">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 rounded-full bg-accent/10 text-accent flex items-center justify-center text-lg font-semibold overflow-hidden">
                    {login.head_img ? (
                      <img src={login.head_img} alt={login.username} className="w-full h-full object-cover" />
                    ) : (
                      login.username.charAt(0).toUpperCase()
                    )}
                  </div>
                  <div>
                    <div className="text-sm font-semibold text-foreground">{login.username}</div>
                    <div className={`text-xs ${isSuccess ? 'text-success' : 'text-danger'}`}>
                      {isSuccess ? '登录成功' : '登录失败'}
                    </div>
                  </div>
                </div>

                <div className="border-t border-divider pt-4 flex flex-col gap-3">
                  <div className="flex justify-between">
                    <span className="text-xs text-muted-foreground">IP 地址</span>
                    <span className="text-xs font-mono text-foreground">{login.ip_address}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-xs text-muted-foreground">登录时间</span>
                    <span className="text-xs text-foreground">{formatTime(login.login_time)}</span>
                  </div>
                </div>
              </div>
            </Modal.Body>
          </Modal.Dialog>
        </Modal.Container>
      </Modal.Backdrop>
    </Modal>
  );
}
