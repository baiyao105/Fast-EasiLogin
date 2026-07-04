import { useState } from 'react';
import { Avatar, Badge, Card, Chip } from '@heroui/react';

interface ElevatedCardWidgetProps {
  name: string;
  userid: string;
  phone?: string;
  headImg?: string;
  status: 'active' | 'inactive';
  onClick?: () => void;
}

function maskPhone(phone: string): string {
  if (!phone || phone.length < 7) return phone || '';
  return phone.slice(0, 3) + '****' + phone.slice(-4);
}

export function ElevatedCardWidget({ name, userid, phone, headImg, status, onClick }: ElevatedCardWidgetProps) {
  const [isHovered, setIsHovered] = useState(false);
  const initial = (name || '?').charAt(0).toUpperCase();
  const isActive = status === 'active';

  return (
    <div
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onClick?.(); }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      className="cursor-pointer transition-transform duration-200 ease-out"
      style={{ transform: isHovered ? 'translateY(-4px)' : 'translateY(0)' }}
    >
      <Card className="transition-shadow duration-200 bg-surface-secondary" style={{ boxShadow: isHovered ? '0 8px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)' : 'none' }}>
        <Card.Content className="flex flex-col items-center gap-3 py-5 px-4">
          <Badge.Anchor>
            <div className="relative">
              <Avatar size="lg" color="accent" variant="soft">
                {headImg ? (
                  <Avatar.Image src={headImg} alt={name} />
                ) : null}
                <Avatar.Fallback>{initial}</Avatar.Fallback>
              </Avatar>
              {/* Hover overlay with blur and edit icon */}
              <div
                className="absolute inset-0 rounded-full flex items-center justify-center transition-opacity duration-200"
                style={{
                  opacity: isHovered ? 1 : 0,
                  backdropFilter: isHovered ? 'blur(2px)' : 'none',
                  backgroundColor: isHovered ? 'rgba(0, 0, 0, 0.3)' : 'transparent'
                }}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                  <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                </svg>
              </div>
            </div>
            {isActive && (
              <Badge color="success" variant="primary" size="sm">
                <svg width="8" height="8" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
                  <polyline points="20 6 9 17 4 12"/>
                </svg>
              </Badge>
            )}
          </Badge.Anchor>

          <div className="text-sm font-semibold text-foreground text-center leading-tight">
            {name || '未命名'}
          </div>

          <div className="text-xs text-muted-foreground font-mono">
            {maskPhone(phone || userid)}
          </div>

          <Chip
            color={isActive ? 'success' : 'default'}
            variant={isActive ? 'soft' : 'secondary'}
            size="sm"
          >
            {isActive ? '可用' : '未激活'}
          </Chip>

          {/* Hover expand section */}
          <div
            className="w-full overflow-hidden transition-all duration-200"
            style={{
              maxHeight: isHovered ? '32px' : '0',
              opacity: isHovered ? 1 : 0,
              marginTop: isHovered ? '4px' : '0'
            }}
          >
            <div className="border-t border-divider pt-2">
              <div className="text-[11px] text-muted-foreground text-center">点击编辑</div>
            </div>
          </div>
        </Card.Content>
      </Card>
    </div>
  );
}
