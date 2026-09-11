import { Avatar } from '@heroui/react';
import type { DashboardAccount } from '@/lib/types';
import { initialFor } from '@/lib/utils';

export function EventIdentity({
  userId,
  fallbackName,
  accountMap,
  size = 'sm',
}: {
  userId?: string | null;
  fallbackName: string;
  accountMap: Map<string, DashboardAccount>;
  size?: 'sm' | 'md';
}) {
  const account = userId ? accountMap.get(userId) : undefined;
  const name = account?.nickname || account?.real_name || fallbackName;
  const avatar = account?.avatar_url;

  return (
    <div className="flex min-w-0 items-center gap-2">
      <Avatar size={size}>
        {avatar ? <Avatar.Image src={avatar} alt="" /> : null}
        <Avatar.Fallback>{initialFor(name)}</Avatar.Fallback>
      </Avatar>
      <span className="truncate font-medium text-foreground">{name}</span>
    </div>
  );
}
