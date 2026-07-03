import { motion } from 'framer-motion';
import { User, Trash } from 'iconoir-react';
import type { Account } from '../../types/api';

interface AccountListProps {
  accounts: Account[] | undefined;
  onDelete: (userid: string) => void;
  isLoading: boolean;
}

export function AccountList({ accounts, onDelete, isLoading }: AccountListProps) {
  if (isLoading) {
    return (
      <div className="account-list">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="account-item" style={{ opacity: 0.5 }}>
            <div className="account-avatar" />
            <div style={{ flex: 1, marginLeft: 12 }}>
              <div style={{ height: 14, width: 80, background: 'var(--bg-surface-hover)', borderRadius: 4, marginBottom: 6 }} />
              <div style={{ height: 12, width: 100, background: 'var(--bg-surface-hover)', borderRadius: 4 }} />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (!accounts || accounts.length === 0) {
    return (
      <div className="card">
        <div className="card-content">
          <div className="empty-state">
            <User className="empty-state-icon" strokeWidth={1.5} />
            <div className="empty-state-title">暂无账户</div>
            <div className="empty-state-desc">点击上方按钮添加第一个账户</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="account-list">
      {accounts.map((account, index) => (
        <motion.div
          key={account.pt_userid}
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: index * 0.03, duration: 0.2 }}
          className="account-item"
        >
          <div className="account-avatar">
            {account.pt_photourl ? (
              <img
                src={account.pt_photourl}
                alt={account.pt_nickname}
              />
            ) : (
              <User width={20} height={20} strokeWidth={1.5} />
            )}
          </div>
          <div className="account-info">
            <div className="account-name">{account.pt_nickname || '未命名'}</div>
            <div className="account-id">{account.pt_userid}</div>
          </div>
          <button
            className="btn btn-ghost"
            style={{ color: 'var(--error)' }}
            onClick={() => onDelete(account.pt_userid)}
          >
            <Trash width={16} height={16} strokeWidth={1.5} />
            删除
          </button>
        </motion.div>
      ))}
    </div>
  );
}
