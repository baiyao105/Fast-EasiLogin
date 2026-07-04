import { motion } from 'framer-motion';
import { Skeleton } from '@heroui/react';
import { ElevatedCardWidget } from './elevated-card';
import type { Account } from '../../types/api';

interface AccountListProps {
  accounts: Account[] | undefined;
  onSelectAccount: (account: Account) => void;
  onDeleteAccount: (account: Account) => void;
  isLoading: boolean;
  hasSearchQuery: boolean;
  onAddAccount: () => void;
}

export function AccountList({ accounts, onSelectAccount, onDeleteAccount, isLoading, hasSearchQuery, onAddAccount }: AccountListProps) {
  if (isLoading) {
    return (
      <div className="flex flex-wrap gap-4">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="w-[200px] bg-card border border-divider rounded-xl p-5 flex flex-col items-center gap-3">
            <Skeleton className="w-14 h-14 rounded-xl" />
            <Skeleton className="w-16 h-3.5 rounded" />
            <Skeleton className="w-20 h-3 rounded" />
            <Skeleton className="w-14 h-5 rounded-full" />
          </div>
        ))}
      </div>
    );
  }

  return (
    <div className="flex flex-wrap gap-4">
      {/* Add account card */}
      <button
        onClick={onAddAccount}
        className="w-[200px] border-2 border-dashed border-divider rounded-xl p-5 flex flex-col items-center justify-center min-h-[220px] cursor-pointer transition-colors hover:border-primary/50 hover:bg-primary/5"
      >
        <div className="w-12 h-12 rounded-full bg-muted flex items-center justify-center mb-3">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="text-muted-foreground">
            <line x1="12" y1="5" x2="12" y2="19"/>
            <line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
        </div>
        <div className="text-xs text-muted-foreground">点击添加新账号</div>
      </button>

      {/* Empty state when no accounts and not searching */}
      {!hasSearchQuery && (!accounts || accounts.length === 0) && (
        <div className="w-full bg-card border border-divider rounded-xl py-12 px-6 text-center">
          <div className="w-16 h-16 rounded-2xl bg-muted flex items-center justify-center mx-auto mb-4">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-muted-foreground">
              <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
              <circle cx="12" cy="7" r="4" />
            </svg>
          </div>
          <div className="text-sm font-semibold text-foreground mb-1">暂无账户</div>
          <div className="text-xs text-muted-foreground">点击加号卡片添加第一个账户</div>
        </div>
      )}

      {/* Search empty state */}
      {hasSearchQuery && (!accounts || accounts.length === 0) && (
        <div className="w-full bg-card border border-divider rounded-xl py-12 px-6 text-center">
          <div className="w-16 h-16 rounded-2xl bg-muted flex items-center justify-center mx-auto mb-4">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="text-muted-foreground">
              <circle cx="11" cy="11" r="8"/>
              <path d="m21 21-4.35-4.35"/>
            </svg>
          </div>
          <div className="text-sm font-semibold text-foreground mb-1">未匹配到账户</div>
          <div className="text-xs text-muted-foreground">请尝试其他搜索关键词</div>
        </div>
      )}

      {/* Account cards */}
      {accounts?.map((account, index) => (
        <motion.div
          key={account.pt_userid}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: index * 0.05, duration: 0.3 }}
          className="w-[200px]"
        >
          <ElevatedCardWidget
            name={account.pt_nickname || '未命名'}
            userid={account.pt_userid}
            phone={account.phone}
            headImg={account.pt_photourl}
            status={account.status}
            onClick={() => onSelectAccount(account)}
          />
        </motion.div>
      ))}
    </div>
  );
}
