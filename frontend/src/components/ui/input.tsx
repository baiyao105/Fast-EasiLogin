import { cn } from '@/lib/utils';
import type { InputHTMLAttributes } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export function Input({
  className,
  label,
  error,
  id,
  ...props
}: InputProps) {
  return (
    <div className="flex flex-col space-y-1.5">
      {label && (
        <label
          htmlFor={id}
          className="text-sm font-medium text-gray-900"
        >
          {label}
        </label>
      )}
      <input
        id={id}
        className={cn(
          'flex h-10 w-full rounded-md bg-surface border border-border px-3 py-2 text-sm',
          'transition-colors duration-150 ease-out',
          'placeholder:text-text-secondary',
          'focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-0',
          'disabled:cursor-not-allowed disabled:opacity-50',
          error && 'border-red-500 focus:ring-red-500',
          className
        )}
        {...props}
      />
      {error && (
        <p className="text-sm text-red-500">{error}</p>
      )}
    </div>
  );
}
