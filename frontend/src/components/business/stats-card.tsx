import { motion } from 'framer-motion';
import { Button, Card } from '@heroui/react';
import type { DashboardStats } from '../../types/api';

interface StatsCardProps {
  stats: DashboardStats | undefined;
}

export function StatsCard({ stats }: StatsCardProps) {
  if (!stats) return null;

  const cards = [
    { 
      label: '服务状态', 
      value: '正常运行',
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-success">
          <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
          <polyline points="22 4 12 14.01 9 11.01"/>
        </svg>
      ),
      subtitle: `http://127.0.0.1:${stats.listen_port}`,
      actions: [
        { label: '重启', variant: 'secondary' as const },
        { label: '测试接口', variant: 'primary' as const }
      ]
    },
    { 
      label: '账号统计', 
      value: stats.total_logins,
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-primary">
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
          <circle cx="9" cy="7" r="4"/>
          <path d="M23 21v-2a4 4 0 0 0-3-3.87"/>
          <path d="M16 3.13a4 4 0 0 1 0 7.75"/>
        </svg>
      ),
      suffix: '个活跃账号',
      footer: [
        { label: '今日登录', value: `${stats.success_logins} 次` }
      ]
    },
    { 
      label: '活跃会话', 
      value: 1,
      icon: (
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-secondary">
          <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
        </svg>
      ),
      suffix: '个会话',
      footer: [
        { label: 'CPU', value: '5%' },
        { label: '内存', value: '48 MB' }
      ]
    }
  ];

  return (
    <div className="grid grid-cols-3 gap-4">
      {cards.map((card, index) => (
        <motion.div
          key={card.label}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.08, duration: 0.3 }}
        >
          <Card className="h-full">
            <Card.Header className="justify-between">
              <div className="flex items-center gap-2.5">
                {card.icon}
                <Card.Title>{card.label}</Card.Title>
              </div>
              <span className="text-xs text-muted-foreground">实时</span>
            </Card.Header>
            <Card.Content className="flex-1 flex flex-col">
              <div className="flex items-baseline gap-1.5 mb-2">
                <span className="text-2xl font-semibold text-foreground leading-none">{card.value}</span>
                {card.suffix && (
                  <span className="text-xs text-muted-foreground">{card.suffix}</span>
                )}
              </div>
              
              {card.subtitle && (
                <div className="text-xs text-muted-foreground font-mono">
                  {card.subtitle}
                </div>
              )}
              
              {card.footer && (
                <div className="mt-auto pt-3 border-t border-divider flex gap-6">
                  {card.footer.map((item) => (
                    <div key={item.label}>
                      <div className="text-xs text-muted-foreground">{item.label}</div>
                      <div className="text-sm font-semibold text-foreground">{item.value}</div>
                    </div>
                  ))}
                </div>
              )}
            </Card.Content>
            {card.actions && (
              <Card.Footer className="flex gap-2 pt-3">
                {card.actions.map((action) => (
                  <Button 
                    key={action.label}
                    variant={action.variant}
                    size="sm"
                    className="flex-1"
                  >
                    {action.label}
                  </Button>
                ))}
              </Card.Footer>
            )}
          </Card>
        </motion.div>
      ))}
    </div>
  );
}
