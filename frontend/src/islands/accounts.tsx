import { useState } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  Button, TextField, Label, Input, Modal, SearchField, AlertDialog, Fieldset, Description, FieldError
} from '@heroui/react';
import { AccountList } from '../components/business/account-list';
import { AccountDialog } from '../components/business/account-dialog';
import { useAccounts, useAddAccount, useDeleteAccount } from '../lib/api/hooks';
import type { Account } from '../types/api';

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
  const [selectedAccount, setSelectedAccount] = useState<Account | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Account | null>(null);
  const [userid, setUserid] = useState('');
  const [password, setPassword] = useState('');
  const [userName, setUserName] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  const { data, isLoading } = useAccounts();
  const addAccount = useAddAccount();
  const deleteAccount = useDeleteAccount();

  const handleAdd = async () => {
    if (!userid || !password) return;
    await addAccount.mutateAsync({ userid, password, user_name: userName });
    setShowAddDialog(false);
    setUserid('');
    setPassword('');
    setUserName('');
  };

  const handleDelete = async (userid: string) => {
    await deleteAccount.mutateAsync(userid);
  };

  const filteredAccounts = data?.data?.filter(account => {
    const q = String(searchQuery || '').toLowerCase();
    if (!q) return true;
    return String(account.pt_userid || '').toLowerCase().includes(q) ||
           String(account.pt_nickname || '').toLowerCase().includes(q) ||
           String(account.phone || '').toLowerCase().includes(q);
  });

  return (
    <>
      <div className="page-header">
        <div className="flex items-center gap-4">
          <div>
            <h1 className="page-title">账户管理</h1>
            <p className="page-subtitle">管理 SSO 登录账户</p>
          </div>
          {/* Total count card */}
          <div className="bg-surface border border-divider rounded-xl px-6 py-3 flex flex-col items-center justify-center min-w-[80px]">
            <div className="text-2xl font-bold text-foreground">{data?.data?.length || 0}</div>
            <div className="text-xs text-muted-foreground">总账号</div>
          </div>
        </div>
      </div>

      <div className="page-content">
        <div className="mb-5">
          <SearchField value={searchQuery} onChange={setSearchQuery} className="max-w-sm">
            <SearchField.Group>
              <SearchField.SearchIcon />
              <SearchField.Input placeholder="搜索用户 ID / 昵称 / 手机号..." />
              <SearchField.ClearButton />
            </SearchField.Group>
          </SearchField>
        </div>

        <AccountList
          accounts={filteredAccounts}
          onSelectAccount={setSelectedAccount}
          onDeleteAccount={setDeleteTarget}
          isLoading={isLoading}
          hasSearchQuery={!!searchQuery}
          onAddAccount={() => setShowAddDialog(true)}
        />
      </div>

      {/* Add Account Modal */}
      <Modal isOpen={showAddDialog} onOpenChange={setShowAddDialog}>
        <Modal.Backdrop>
          <Modal.Container placement="center" size="md">
            <Modal.Dialog>
              <Modal.CloseTrigger />
              <Modal.Header>
                <Modal.Heading>添加账户</Modal.Heading>
              </Modal.Header>
              <Modal.Body>
                <Fieldset className="w-full">
                  <Fieldset.Legend>账户信息</Fieldset.Legend>
                  <Description>请输入 SSO 登录账户的凭据。</Description>
                  <Fieldset.Group className="flex flex-col gap-4">
                    <TextField isRequired>
                      <Label>用户ID</Label>
                      <Input placeholder="请输入用户ID" variant="secondary" value={userid} onChange={(e: any) => setUserid(e?.target?.value ?? String(e ?? ''))} />
                      <FieldError />
                    </TextField>
                    <TextField isRequired>
                      <Label>密码</Label>
                      <Input type="password" placeholder="请输入密码" variant="secondary" value={password} onChange={(e: any) => setPassword(e?.target?.value ?? String(e ?? ''))} />
                      <FieldError />
                    </TextField>
                    <TextField>
                      <Label>用户名（可选）</Label>
                      <Input placeholder="请输入用户名" variant="secondary" value={userName} onChange={(e: any) => setUserName(e?.target?.value ?? String(e ?? ''))} />
                    </TextField>
                  </Fieldset.Group>
                  <Fieldset.Actions className="justify-end gap-2 pt-4">
                    <Button variant="tertiary" onPress={() => setShowAddDialog(false)}>取消</Button>
                    <Button variant="primary" onPress={handleAdd} isDisabled={!userid || !password}>添加</Button>
                  </Fieldset.Actions>
                </Fieldset>
              </Modal.Body>
            </Modal.Dialog>
          </Modal.Container>
        </Modal.Backdrop>
      </Modal>

      {/* Account Detail Dialog */}
      {selectedAccount && (
        <AccountDialog
          account={selectedAccount}
          isOpen={!!selectedAccount}
          onClose={() => setSelectedAccount(null)}
          onDeleteRequest={(account) => {
            setSelectedAccount(null);
            setDeleteTarget(account);
          }}
        />
      )}

      {/* Delete Confirmation AlertDialog */}
      <AlertDialog isOpen={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <AlertDialog.Backdrop>
          <AlertDialog.Container placement="center" size="sm">
            <AlertDialog.Dialog>
              <AlertDialog.CloseTrigger />
              <AlertDialog.Header>
                <AlertDialog.Icon status="danger" />
                <AlertDialog.Heading>确认删除</AlertDialog.Heading>
              </AlertDialog.Header>
              <AlertDialog.Body>
                <p>确定要删除账户 <strong>{deleteTarget?.pt_nickname || deleteTarget?.pt_userid}</strong> 吗？此操作不可撤销。</p>
              </AlertDialog.Body>
              <AlertDialog.Footer>
                <Button variant="secondary" onPress={() => setDeleteTarget(null)}>取消</Button>
                <Button
                  variant="danger"
                  onPress={() => {
                    if (deleteTarget) {
                      handleDelete(deleteTarget.pt_userid);
                      setDeleteTarget(null);
                    }
                  }}
                >
                  删除
                </Button>
              </AlertDialog.Footer>
            </AlertDialog.Dialog>
          </AlertDialog.Container>
        </AlertDialog.Backdrop>
      </AlertDialog>
    </>
  );
}
