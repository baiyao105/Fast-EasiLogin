import { PersonPlus } from '@gravity-ui/icons';
import { Button, SearchField, toast } from '@heroui/react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { AccountCard } from '@/components/account-card';
import { AccountDetailModal } from '@/components/account-detail';
import { AddAccountDialog } from '@/components/add-account-dialog';
import { ConfirmDialog } from '@/components/confirm-dialog';
import { FilterToggleGroup } from '@/components/filter-toggle-group';
import { PageHeader } from '@/components/page-header';
import { EmptyState, ErrorState, LoadingState } from '@/components/ui-states';
import {
  useAccounts,
  useDeleteAccount,
  useRefreshAccount,
  useToggleAccountActive,
} from '@/hooks/use-dashboard';
import type { DashboardAccount } from '@/lib/types';

type ActiveFilter = 'all' | 'active' | 'inactive';

const FILTERS: Array<{ id: ActiveFilter; label: string }> = [
  { id: 'all', label: '全部' },
  { id: 'active', label: '启用' },
  { id: 'inactive', label: '停用' },
];

export function AccountsPage() {
  const [query, setQuery] = useState('');
  const [debouncedQuery, setDebouncedQuery] = useState('');
  const [filter, setFilter] = useState<ActiveFilter>('all');
  const [page, setPage] = useState(1);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [detailAccount, setDetailAccount] = useState<DashboardAccount | null>(
    null,
  );
  const [pendingDelete, setPendingDelete] = useState<DashboardAccount | null>(
    null,
  );
  const [selectMode, setSelectMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set());
  const [batchRefreshing, setBatchRefreshing] = useState(false);
  const autoRefreshed = useRef<string | null>(null);
  const pageSize = 12;

  useEffect(() => {
    const timer = window.setTimeout(() => setDebouncedQuery(query), 250);
    return () => window.clearTimeout(timer);
  }, [query]);

  const active = filter === 'all' ? null : filter === 'active';
  const accounts = useAccounts({
    page,
    page_size: pageSize,
    q: debouncedQuery.trim() || undefined,
    active,
  });
  const toggleActive = useToggleAccountActive();
  const deleteAccount = useDeleteAccount();
  const refreshAccount = useRefreshAccount();

  const items = accounts.data?.items ?? [];
  const total = accounts.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));

  async function handleToggle(account: DashboardAccount) {
    try {
      await toggleActive.mutateAsync({
        userId: account.user_id,
        active: !account.active,
      });
      toast.success(account.active ? '账号已停用' : '账号已启用');
      await accounts.refetch();
      setDetailAccount((prev) =>
        prev && prev.user_id === account.user_id
          ? { ...prev, active: !account.active }
          : prev,
      );
    } catch (err) {
      toast.danger(err instanceof Error ? err.message : '操作失败');
    }
  }

  const handleRefresh = useCallback(
    async (account: DashboardAccount, silent = false) => {
      try {
        const next = await refreshAccount.mutateAsync(account.user_id);
        setDetailAccount(next);
        await accounts.refetch();
        if (!next.active) {
          toast.warning('账号登录失败，已自动停用');
        } else if (!silent) {
          toast.success('账号已刷新');
        }
      } catch (err) {
        toast.danger(err instanceof Error ? err.message : '刷新失败');
      }
    },
    [accounts, refreshAccount],
  );

  useEffect(() => {
    if (!detailAccount) {
      autoRefreshed.current = null;
      return;
    }
    if (autoRefreshed.current === detailAccount.user_id) {
      return;
    }
    autoRefreshed.current = detailAccount.user_id;
    void handleRefresh(detailAccount, true);
  }, [detailAccount, handleRefresh]);

  function toggleSelect(userId: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(userId)) {
        next.delete(userId);
      } else {
        next.add(userId);
      }
      return next;
    });
  }

  function selectAll() {
    setSelectedIds(new Set(items.map((item) => item.user_id)));
  }

  function clearSelection() {
    setSelectedIds(new Set());
  }

  function exitSelectMode() {
    setSelectMode(false);
    clearSelection();
  }

  async function handleBatchRefresh() {
    if (selectedIds.size === 0) {
      return;
    }
    setBatchRefreshing(true);
    let ok = 0;
    let disabled = 0;
    for (const userId of selectedIds) {
      try {
        const next = await refreshAccount.mutateAsync(userId);
        if (next.active) {
          ok += 1;
        } else {
          disabled += 1;
        }
      } catch {
        // continue others
      }
    }
    await accounts.refetch();
    setBatchRefreshing(false);
    exitSelectMode();
    if (disabled > 0) {
      toast.warning(`刷新完成：成功 ${ok}，自动停用 ${disabled}`);
    } else {
      toast.success(`已刷新 ${ok} 个账号`);
    }
  }

  async function handleDelete() {
    if (!pendingDelete) {
      return;
    }
    try {
      await deleteAccount.mutateAsync(pendingDelete.user_id);
      toast.success('账号已删除');
      setPendingDelete(null);
      setDetailAccount(null);
    } catch (err) {
      toast.danger(err instanceof Error ? err.message : '删除失败');
    }
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="账号"
        description={
          selectMode
            ? '点击账号卡片进行选中，然后批量刷新资料。'
            : '管理本地保存的 Seewo 账号。添加前会先验证凭据，浏览器不会保存密码。'
        }
        actions={
          selectMode ? (
            <>
              <Button
                variant="secondary"
                onPress={
                  selectedIds.size === items.length && items.length > 0
                    ? clearSelection
                    : selectAll
                }
              >
                {selectedIds.size === items.length && items.length > 0
                  ? '取消全选'
                  : '全选'}
              </Button>
              <Button variant="ghost" onPress={exitSelectMode}>
                退出选择
              </Button>
              <Button
                isDisabled={selectedIds.size === 0 || batchRefreshing}
                onPress={() => void handleBatchRefresh()}
              >
                {batchRefreshing ? '刷新中…' : `刷新账号 (${selectedIds.size})`}
              </Button>
            </>
          ) : (
            <>
              <Button
                variant="secondary"
                onPress={() => {
                  setSelectMode(true);
                  clearSelection();
                }}
              >
                刷新账号
              </Button>
              <Button onPress={() => setDrawerOpen(true)}>添加账号</Button>
            </>
          )
        }
      />

      {!selectMode ? (
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <SearchField
            className="w-full sm:max-w-sm"
            value={query}
            onChange={(value) => {
              setQuery(value);
              setPage(1);
            }}
            aria-label="搜索账号"
          >
            <SearchField.Group>
              <SearchField.SearchIcon />
              <SearchField.Input placeholder="搜索昵称或用户 ID" />
              <SearchField.ClearButton />
            </SearchField.Group>
          </SearchField>
          <FilterToggleGroup
            label="账号状态筛选"
            value={filter}
            options={FILTERS}
            onChange={(next) => {
              setFilter(next);
              setPage(1);
            }}
          />
        </div>
      ) : null}

      {accounts.isLoading ? (
        <LoadingState label="加载账号…" />
      ) : accounts.error ? (
        <ErrorState
          message={
            accounts.error instanceof Error
              ? accounts.error.message
              : '账号加载失败'
          }
          onRetry={() => accounts.refetch()}
        />
      ) : items.length === 0 ? (
        debouncedQuery.trim() || filter !== 'all' ? (
          <EmptyState
            icon={<PersonPlus className="size-6" aria-hidden />}
            title="当前筛选条件下无账号"
            description="试试调整搜索关键词或状态筛选。"
            action={
              <Button
                variant="secondary"
                onPress={() => {
                  setQuery('');
                  setFilter('all');
                  setPage(1);
                }}
              >
                清除筛选
              </Button>
            }
          />
        ) : (
          <EmptyState
            icon={<PersonPlus className="size-6" aria-hidden />}
            title="还没有添加账号哦"
            description="添加账号后即可开始工作啦!"
            action={
              <Button onPress={() => setDrawerOpen(true)}>添加账号</Button>
            }
          />
        )
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {items.map((account) => (
              <AccountCard
                key={account.user_id}
                account={account}
                busy={
                  selectMode
                    ? batchRefreshing
                    : toggleActive.isPending || deleteAccount.isPending
                }
                selectMode={selectMode}
                selected={selectedIds.has(account.user_id)}
                onDetail={() => setDetailAccount(account)}
                onDelete={() => setPendingDelete(account)}
                onToggleSelect={() => toggleSelect(account.user_id)}
              />
            ))}
          </div>

          <div className="page-card flex items-center justify-between gap-3 px-4 py-3 text-sm text-muted">
            <span>
              共 {total} 条 · 第 {page}/{totalPages} 页
            </span>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="secondary"
                isDisabled={page <= 1}
                onPress={() => setPage((p) => Math.max(1, p - 1))}
              >
                上一页
              </Button>
              <Button
                size="sm"
                variant="secondary"
                isDisabled={page >= totalPages}
                onPress={() => setPage((p) => Math.min(totalPages, p + 1))}
              >
                下一页
              </Button>
            </div>
          </div>
        </>
      )}

      <AddAccountDialog open={drawerOpen} onOpenChange={setDrawerOpen} />

      <AccountDetailModal
        open={Boolean(detailAccount)}
        onOpenChange={(open) => {
          if (!open) {
            setDetailAccount(null);
          }
        }}
        title="账号详情"
        profile={
          detailAccount
            ? {
                user_id: detailAccount.user_id,
                phone: detailAccount.phone,
                nickname: detailAccount.nickname,
                real_name: detailAccount.real_name,
                avatar_url: detailAccount.avatar_url,
                active: detailAccount.active,
                last_login_at: detailAccount.last_login_at,
                created_at: detailAccount.created_at,
                school: detailAccount.school,
                stage_name: detailAccount.stage_name,
                subject_name: detailAccount.subject_name,
              }
            : null
        }
        footerActions={
          detailAccount ? (
            <>
              <Button
                size="sm"
                variant="secondary"
                isDisabled={refreshAccount.isPending}
                onPress={() => void handleRefresh(detailAccount)}
              >
                {refreshAccount.isPending ? '刷新中…' : '刷新账号'}
              </Button>
              <Button
                size="sm"
                variant="secondary"
                isDisabled={toggleActive.isPending}
                onPress={() => void handleToggle(detailAccount)}
              >
                {detailAccount.active ? '停用' : '启用'}
              </Button>
              <Button
                size="sm"
                variant="danger-soft"
                onPress={() => {
                  setPendingDelete(detailAccount);
                  setDetailAccount(null);
                }}
              >
                删除
              </Button>
            </>
          ) : null
        }
      />

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        onOpenChange={(open) => {
          if (!open) {
            setPendingDelete(null);
          }
        }}
        title="删除账号"
        description={`确认删除「${pendingDelete?.nickname || pendingDelete?.user_id || ''}」？本地凭据将一并移除，此操作不可撤销。`}
        confirmLabel="删除"
        loading={deleteAccount.isPending}
        onConfirm={() => void handleDelete()}
      />
    </div>
  );
}
