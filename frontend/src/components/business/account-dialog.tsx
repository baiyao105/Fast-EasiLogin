import { Avatar, Button, Modal, Separator } from '@heroui/react';
import type { Account } from '../../types/api';

interface AccountDialogProps {
  account: Account;
  isOpen: boolean;
  onClose: () => void;
  onDeleteRequest: (account: Account) => void;
}

function maskPhone(phone: string): string {
  if (!phone || phone.length < 7) return phone || '';
  return phone.slice(0, 3) + '****' + phone.slice(-4);
}

export function AccountDialog({ account, isOpen, onClose, onDeleteRequest }: AccountDialogProps) {
  const initial = (account.pt_nickname || '?').charAt(0).toUpperCase();
  const isActive = account.status === 'active';

  return (
    <Modal isOpen={isOpen} onOpenChange={onClose}>
      <Modal.Backdrop>
        <Modal.Container placement="center" size="md">
          <Modal.Dialog>
            <Modal.CloseTrigger />
            <Modal.Header>
              <div className="flex items-center gap-3">
                <Avatar size="lg" color="accent" variant="soft">
                  {account.pt_photourl ? (
                    <Avatar.Image src={account.pt_photourl} alt={account.pt_nickname} />
                  ) : null}
                  <Avatar.Fallback>{initial}</Avatar.Fallback>
                </Avatar>
                <Modal.Heading>{account.pt_nickname || '未命名'}</Modal.Heading>
              </div>
            </Modal.Header>
            <Modal.Body>
              <div className="flex min-h-[280px]">
                {/* Left: info */}
                <div className="flex-[0_0_45%] pr-5 border-r border-divider flex flex-col gap-3">
                  <div>
                    <div className="text-xs text-muted-foreground mb-0.5">用户ID</div>
                    <div className="text-sm text-foreground font-mono">{account.pt_userid}</div>
                  </div>
                  <Separator />
                  <div>
                    <div className="text-xs text-muted-foreground mb-0.5">手机号</div>
                    <div className="text-sm text-foreground font-mono">{maskPhone(account.phone) || '未设置'}</div>
                  </div>
                  <Separator />
                  <div>
                    <div className="text-xs text-muted-foreground mb-0.5">状态</div>
                    <div className={`text-sm flex items-center gap-1.5 ${isActive ? 'text-success' : 'text-muted-foreground'}`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${isActive ? 'bg-success' : 'bg-muted-foreground'}`} />
                      {isActive ? '活跃' : '未激活'}
                    </div>
                  </div>
                </div>

                {/* Right: actions */}
                <div className="flex-1 pl-5 flex flex-col gap-2">
                  <div className="text-sm font-semibold text-foreground mb-2">操作</div>
                  <Button variant="secondary" className="justify-start" startContent={
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                    </svg>
                  }>
                    编辑资料
                  </Button>
                  <Button variant="secondary" className="justify-start" startContent={
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="23 4 23 10 17 10"/>
                      <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10"/>
                    </svg>
                  }>
                    重新登录
                  </Button>
                  <div className="flex-1" />
                  <Button variant="danger" className="justify-start" onPress={() => {
                    onClose();
                    onDeleteRequest(account);
                  }} startContent={
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="3 6 5 6 21 6"/>
                      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/>
                    </svg>
                  }>
                    删除账户
                  </Button>
                </div>
              </div>
            </Modal.Body>
          </Modal.Dialog>
        </Modal.Container>
      </Modal.Backdrop>
    </Modal>
  );
}
