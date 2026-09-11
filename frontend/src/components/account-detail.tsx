import { Avatar, Button, Chip, Modal } from '@heroui/react';
import type { ReactNode } from 'react';
import { formatDateTime, initialFor } from '@/lib/utils';

export type AccountProfile = {
  user_id: string;
  phone?: string | null;
  nickname?: string;
  real_name?: string | null;
  avatar_url?: string;
  active?: boolean;
  last_login_at?: string | null;
  created_at?: string | null;
  school?: string | null;
  stage_name?: string | null;
  subject_name?: string | null;
};

function InfoItem({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="min-w-0 rounded-xl bg-default/50 px-3 py-2.5">
      <div className="text-xs text-muted">{label}</div>
      <div className="mt-1 break-words text-sm font-medium text-foreground">
        {value || '—'}
      </div>
    </div>
  );
}

export function AccountDetailContent({
  profile,
  showPhone = false,
  showTimestamps = true,
}: {
  profile: AccountProfile;
  /** 仅在添加账号验证确认时展示明文手机号 */
  showPhone?: boolean;
  /** 添加账号确认时隐藏最近活跃/创建时间 */
  showTimestamps?: boolean;
}) {
  const name = profile.nickname || profile.real_name || profile.user_id;
  return (
    <div className="space-y-5">
      <div className="flex items-center gap-3">
        <Avatar size="lg">
          {profile.avatar_url ? (
            <Avatar.Image src={profile.avatar_url} alt="" />
          ) : null}
          <Avatar.Fallback>{initialFor(name)}</Avatar.Fallback>
        </Avatar>
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="truncate text-lg font-semibold text-foreground">
              {name}
            </h3>
            {profile.active !== undefined ? (
              <Chip color={profile.active ? 'success' : 'default'} size="sm">
                {profile.active ? '启用' : '停用'}
              </Chip>
            ) : null}
          </div>
          <p className="mt-0.5 truncate text-sm text-muted">
            {profile.real_name || profile.user_id}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <InfoItem label="用户 ID" value={profile.user_id} />
        {showPhone ? <InfoItem label="手机号" value={profile.phone} /> : null}
        <InfoItem label="学校" value={profile.school} />
        <InfoItem label="学段" value={profile.stage_name} />
        <InfoItem label="学科" value={profile.subject_name} />
        {showTimestamps ? (
          <>
            <InfoItem
              label="最近活跃"
              value={
                profile.last_login_at
                  ? formatDateTime(profile.last_login_at)
                  : null
              }
            />
            <InfoItem
              label="创建时间"
              value={
                profile.created_at ? formatDateTime(profile.created_at) : null
              }
            />
          </>
        ) : null}
      </div>
    </div>
  );
}

export function AccountDetailModal({
  open,
  onOpenChange,
  title = '账号详情',
  profile,
  showPhone = false,
  showTimestamps = true,
  confirmLabel,
  cancelLabel,
  loading,
  onConfirm,
  children,
  footerActions,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title?: string;
  profile: AccountProfile | null;
  showPhone?: boolean;
  showTimestamps?: boolean;
  confirmLabel?: string;
  cancelLabel?: string;
  loading?: boolean;
  onConfirm?: () => void;
  children?: ReactNode;
  footerActions?: ReactNode;
}) {
  if (!profile) {
    return null;
  }

  return (
    <Modal isOpen={open} onOpenChange={onOpenChange}>
      <Modal.Backdrop isDismissable={false}>
        <Modal.Container placement="center" size="lg">
          <Modal.Dialog>
            <Modal.CloseTrigger />
            <Modal.Header>
              <Modal.Heading>{title}</Modal.Heading>
            </Modal.Header>
            <Modal.Body>
              <AccountDetailContent
                profile={profile}
                showPhone={showPhone}
                showTimestamps={showTimestamps}
              />
              {children}
            </Modal.Body>
            <Modal.Footer className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex flex-wrap gap-2">{footerActions}</div>
              <div className="ml-auto flex gap-2">
                {onConfirm ? (
                  <>
                    <Button
                      variant="secondary"
                      isDisabled={loading}
                      onPress={() => onOpenChange(false)}
                    >
                      {cancelLabel ?? '取消'}
                    </Button>
                    <Button isDisabled={loading} onPress={onConfirm}>
                      {loading ? '处理中…' : (confirmLabel ?? '确认')}
                    </Button>
                  </>
                ) : (
                  <Button onPress={() => onOpenChange(false)}>关闭</Button>
                )}
              </div>
            </Modal.Footer>
          </Modal.Dialog>
        </Modal.Container>
      </Modal.Backdrop>
    </Modal>
  );
}
