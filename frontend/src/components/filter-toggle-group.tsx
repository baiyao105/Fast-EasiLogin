import { ToggleButton, ToggleButtonGroup } from '@heroui/react';

export function FilterToggleGroup<T extends string>({
  label,
  value,
  options,
  onChange,
  size = 'sm',
  className,
}: {
  label: string;
  value: T;
  options: Array<{ id: T; label: string }>;
  onChange: (value: T) => void;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}) {
  return (
    <ToggleButtonGroup
      aria-label={label}
      className={className}
      size={size}
      selectionMode="single"
      disallowEmptySelection
      selectedKeys={new Set([value])}
      onSelectionChange={(keys) => {
        const next = Array.from(keys)[0];
        if (typeof next === 'string') {
          onChange(next as T);
        }
      }}
    >
      {options.map((option, index) => (
        <ToggleButton key={option.id} id={option.id}>
          {index > 0 ? <ToggleButtonGroup.Separator /> : null}
          {option.label}
        </ToggleButton>
      ))}
    </ToggleButtonGroup>
  );
}
