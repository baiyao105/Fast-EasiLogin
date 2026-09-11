import type { ReactNode } from 'react';

export function PageHeader({
  title,
  description,
  actions,
  className,
}: {
  title: string;
  description?: string;
  actions?: ReactNode;
  className?: string;
}) {
  return (
    <div
      className={`flex flex-wrap items-start justify-between gap-4 ${
        className ?? ''
      }`}
    >
      <div className="flex min-w-0 flex-col gap-1">
        <h1 className="text-2xl font-bold text-balance">{title}</h1>
        {description ? (
          <p className="text-pretty text-sm text-muted">{description}</p>
        ) : null}
      </div>
      {actions ? (
        <div className="flex shrink-0 items-center gap-2">{actions}</div>
      ) : null}
    </div>
  );
}
