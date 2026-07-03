import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';
import { Plus, X } from 'iconoir-react';
import { AccountList } from '../components/business/account-list';
import { useAccounts, useAddAccount, useDeleteAccount } from '../lib/api/hooks';

const queryClient = new QueryClient();

export function AccountsIsland() {
  return (
    <QueryClientProvider client={queryClient}>
      <AccountsInner />
    </QueryClientProvider>
  );
}

function AccountsInner() {
  const [showAddDialog, setShowAddDialog] = useState(false);
  const [userid, setUserid] = useState('');
  const [password, setPassword] = useState('');
  const [userName, setUserName] = useState('');
  
  const { data, isLoading } = useAccounts();
  const addAccount = useAddAccount();
  const deleteAccount = useDeleteAccount();
  
  const handleAdd = async () => {
    if (!userid || !password) return;
    
    await addAccount.mutateAsync({
      userid,
      password,
      user_name: userName
    });
    
    setShowAddDialog(false);
    setUserid('');
    setPassword('');
    setUserName('');
  };
  
  const handleDelete = async (userid: string) => {
    if (confirm('确定要删除这个账户吗？')) {
      await deleteAccount.mutateAsync(userid);
    }
  };
  
  return (
    <>
      <div className="page-header">
        <h1 className="page-title">账户管理</h1>
        <button className="btn btn-primary" onClick={() => setShowAddDialog(true)}>
          <Plus width={16} height={16} strokeWidth={2} />
          添加账户
        </button>
      </div>
      
      <div className="page-container">
        <AccountList
          accounts={data?.data}
          onDelete={handleDelete}
          isLoading={isLoading}
        />
      </div>
      
      {showAddDialog && (
        <div className="dialog-overlay" onClick={() => setShowAddDialog(false)}>
          <div className="dialog" onClick={(e) => e.stopPropagation()}>
            <div className="dialog-header">
              <h2 className="dialog-title">添加账户</h2>
              <button className="btn btn-ghost btn-icon" onClick={() => setShowAddDialog(false)}>
                <X width={18} height={18} strokeWidth={2} />
              </button>
            </div>
            
            <div className="dialog-body">
              <div>
                <label className="label">用户ID</label>
                <input
                  type="text"
                  className="input"
                  value={userid}
                  onChange={(e) => setUserid(e.target.value)}
                  placeholder="请输入用户ID"
                />
              </div>
              
              <div>
                <label className="label">密码</label>
                <input
                  type="password"
                  className="input"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="请输入密码"
                />
              </div>
              
              <div>
                <label className="label">用户名（可选）</label>
                <input
                  type="text"
                  className="input"
                  value={userName}
                  onChange={(e) => setUserName(e.target.value)}
                  placeholder="请输入用户名"
                />
              </div>
            </div>
            
            <div className="dialog-footer">
              <button className="btn btn-secondary" onClick={() => setShowAddDialog(false)}>
                取消
              </button>
              <button
                className="btn btn-primary"
                onClick={handleAdd}
                disabled={!userid || !password}
              >
                添加
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
