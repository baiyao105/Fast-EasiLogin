import { Box } from '@gravity-ui/icons';
import { Button, Spinner } from '@heroui/react';
import type { ReactNode } from 'react';

export function LoadingState({ label = '加载中…' }: { label?: string }) {
  return (
    <div className="flex min-h-40 items-center justify-center gap-3 text-sm text-muted">
      <Spinner size="sm" />
      <span>{label}</span>
    </div>
  );
}

export function EmptyState({
  title,
  description,
  icon,
  action,
}: {
  title: string;
  description?: string;
  icon?: ReactNode;
  action?: ReactNode;
}) {
  return (
    <div className="flex min-h-44 flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-separator px-6 py-12 text-center">
      {icon ? (
        <div className="flex size-12 items-center justify-center rounded-2xl bg-accent/10 text-accent">
          {icon}
        </div>
      ) : (
        <div className="flex size-12 items-center justify-center rounded-2xl bg-default text-muted">
          <Box className="size-6" aria-hidden />
        </div>
      )}
      <div className="text-base font-medium">{title}</div>
      {description ? (
        <p className="max-w-md text-sm leading-6 text-muted">{description}</p>
      ) : null}
      {action}
    </div>
  );
}

export function ErrorState({
  message,
  onRetry,
}: {
  message: string;
  onRetry?: () => void;
}) {
  return (
    <div className="flex min-h-40 flex-col items-center justify-center gap-3 rounded-2xl border border-danger/20 bg-danger/5 px-6 py-10 text-center">
      <div className="text-sm font-medium text-danger">{message}</div>
      {onRetry ? (
        <Button size="sm" variant="secondary" onPress={onRetry}>
          重试
        </Button>
      ) : null}
    </div>
  );
}
