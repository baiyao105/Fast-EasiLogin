import { motion } from 'framer-motion';
import { User, Trash, Plus, X, Dashboard, Settings, Search, CheckCircle, XmarkCircle } from 'iconoir-react';
import type { DashboardStats } from '../../types/api';

interface StatsCardProps {
  stats: DashboardStats | undefined;
}

export function StatsCard({ stats }: StatsCardProps) {
  if (!stats) return null;

  const cards = [
    { label: '总登录', value: stats.total_logins, color: '', icon: Search },
    { label: '成功', value: stats.success_logins, color: 'success', icon: CheckCircle },
    { label: '失败', value: stats.failed_logins, color: 'error', icon: XmarkCircle },
    { label: '端口', value: stats.listen_port, color: '', icon: Settings }
  ];

  return (
    <div className="stat-grid">
      {cards.map((card, index) => (
        <motion.div
          key={card.label}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.05, duration: 0.3 }}
          className="stat-card"
        >
          <div className="stat-label">{card.label}</div>
          <div className={`stat-value ${card.color}`}>
            {card.value}
          </div>
        </motion.div>
      ))}
    </div>
  );
}

export { User, Trash, Plus, X, Dashboard, Settings };
