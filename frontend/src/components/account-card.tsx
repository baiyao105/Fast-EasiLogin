import { Avatar, Button, Chip } from '@heroui/react';
import type { DashboardAccount } from '@/lib/types';
import { formatRelativeTime, initialFor } from '@/lib/utils';

function InfoCol({
  label,
  value,
}: {
  label: string;
  value: string | null | undefined;
}) {
  return (
    <div className="min-w-0">
      <div className="text-xs text-muted">{label}</div>
      <div className="mt-0.5 truncate text-sm font-medium text-foreground">
        {value || '—'}
      </div>
    </div>
  );
}

export function AccountCard({
  account,
  busy,
  selected = false,
  selectMode = false,
  onDetail,
  onDelete,
  onToggleSelect,
}: {
  account: DashboardAccount;
  busy?: boolean;
  selected?: boolean;
  selectMode?: boolean;
  onDetail: () => void;
  onDelete: () => void;
  onToggleSelect?: () => void;
}) {
  return (
    // biome-ignore lint/a11y/useKeyWithClickEvents: 卡片内已有可聚焦按钮
    <article
      className={`page-card p-5 transition ${
        selectMode
          ? selected
            ? 'cursor-pointer border-accent ring-2 ring-accent/40'
            : 'cursor-pointer hover:border-accent/40'
          : 'cursor-pointer hover:border-accent/30'
      }`}
      onClick={(event) => {
        if ((event.target as HTMLElement).closest('button')) {
          return;
        }
        if (selectMode) {
          onToggleSelect?.();
          return;
        }
        onDetail();
      }}
    >
      {selectMode && selected ? (
        <div className="mb-2 text-xs font-medium text-accent">已选中</div>
      ) : null}
      <div className="flex items-start gap-3">
        <Avatar size="md">
          {account.avatar_url ? (
            <Avatar.Image src={account.avatar_url} alt="" />
          ) : null}
          <Avatar.Fallback>
            {initialFor(account.nickname || account.user_id)}
          </Avatar.Fallback>
        </Avatar>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <h3 className="truncate text-[15px] font-semibold text-foreground">
              {account.nickname || account.user_id}
            </h3>
            <Chip color={account.active ? 'success' : 'default'} size="sm">
              {account.active ? '启用' : '停用'}
            </Chip>
          </div>
          <p className="mt-1 truncate text-xs text-muted">
            {account.real_name || account.phone || account.user_id}
          </p>
        </div>
      </div>

      <div className="mt-4 grid grid-cols-2 gap-x-4 gap-y-3">
        <InfoCol label="学校" value={account.school} />
        <InfoCol label="学段" value={account.stage_name} />
        <InfoCol label="学科" value={account.subject_name} />
        <InfoCol
          label="最近活跃"
          value={formatRelativeTime(account.last_login_at)}
        />
      </div>

      <div className="mt-5 flex flex-wrap gap-2">
        {selectMode ? (
          <Button
            size="sm"
            variant={selected ? 'primary' : 'secondary'}
            isDisabled={busy}
            onPress={onToggleSelect}
          >
            {selected ? '取消选择' : '选择'}
          </Button>
        ) : (
          <>
            <Button
              size="sm"
              variant="secondary"
              isDisabled={busy}
              onPress={onDetail}
            >
              详情
            </Button>
            <Button
              size="sm"
              variant="danger-soft"
              isDisabled={busy}
              onPress={onDelete}
            >
              删除
            </Button>
          </>
        )}
      </div>
    </article>
  );
}
