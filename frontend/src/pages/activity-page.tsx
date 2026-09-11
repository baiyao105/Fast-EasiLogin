import {
  Button,
  DateField,
  DateRangePicker,
  Label,
  Modal,
  RangeCalendar,
  toast,
} from '@heroui/react';
import {
  CalendarDate,
  type DateValue,
  getLocalTimeZone,
  today,
} from '@internationalized/date';
import { useMemo, useState } from 'react';
import { EventIdentity } from '@/components/event-identity';
import { FilterToggleGroup } from '@/components/filter-toggle-group';
import { PageHeader } from '@/components/page-header';
import { StatusPill } from '@/components/status-pill';
import { EmptyState, ErrorState, LoadingState } from '@/components/ui-states';
import {
  useAccounts,
  useLoginEvents,
  useLoginSummary,
  usePruneLoginEvents,
} from '@/hooks/use-dashboard';
import type { DashboardAccount } from '@/lib/types';
import { formatDateTime } from '@/lib/utils';

const STATUS_OPTIONS = [
  { id: 'all', label: '全部' },
  { id: 'success', label: '成功' },
  { id: 'invalid_credentials', label: '凭据无效' },
  { id: 'disabled', label: '账号禁用' },
  { id: 'upstream', label: '上游异常' },
  { id: 'system', label: '系统错误' },
] as const;

type StatusFilter = (typeof STATUS_OPTIONS)[number]['id'];

const SUMMARY_LABELS: Record<string, string> = {
  success: '成功',
  invalid_credentials: '凭据无效',
  disabled: '账号禁用',
  upstream: '上游异常',
  system: '系统错误',
};

function defaultRange() {
  const end = today(getLocalTimeZone());
  return {
    start: new CalendarDate(2020, 1, 1),
    end,
  };
}

export function ActivityPage() {
  const [status, setStatus] = useState<StatusFilter>('all');
  const [page, setPage] = useState(1);
  const [pruneOpen, setPruneOpen] = useState(false);
  const [range, setRange] = useState<{
    start: DateValue;
    end: DateValue;
  } | null>(() => defaultRange());
  const pageSize = 20;

  const events = useLoginEvents({
    page,
    page_size: pageSize,
    status: status === 'all' ? null : status,
  });
  const accountList = useAccounts({ page: 1, page_size: 100 });
  const accountMap = useMemo(() => {
    const map = new Map<string, DashboardAccount>();
    for (const account of accountList.data?.items ?? []) {
      map.set(account.user_id, account);
    }
    return map;
  }, [accountList.data]);
  const summary = useLoginSummary(24);
  const prune = usePruneLoginEvents();

  const items = events.data?.items ?? [];
  const total = events.data?.total ?? 0;
  const totalPages = Math.max(1, Math.ceil(total / pageSize));
  const counts = summary.data?.counts ?? {};

  function openPrune() {
    setRange(defaultRange());
    setPruneOpen(true);
  }

  async function handlePrune() {
    if (!range?.end) {
      toast.danger('请选择清理日期范围');
      return;
    }
    const end = range.end as CalendarDate;
    const iso = new Date(
      Date.UTC(end.year, end.month - 1, end.day, 23, 59, 59, 999),
    ).toISOString();
    try {
      const result = await prune.mutateAsync(iso);
      toast.success(`已清理 ${result.deleted} 条历史事件`);
      setPruneOpen(false);
      await events.refetch();
      await summary.refetch();
    } catch (err) {
      toast.danger(err instanceof Error ? err.message : '清理失败');
    }
  }

  return (
    <div className="space-y-5">
      <PageHeader
        title="活动"
        description="登录事件时间线。可按状态筛选，并在确认后清理历史记录。"
        actions={
          <Button variant="danger-soft" onPress={openPrune}>
            清理历史
          </Button>
        }
      />

      <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {Object.keys(counts).length === 0 ? (
          <div className="page-card sm:col-span-2 xl:col-span-4">
            <p className="px-5 py-4 text-sm text-muted">
              暂无 24 小时汇总数据。
            </p>
          </div>
        ) : (
          Object.entries(counts).map(([key, value]) => (
            <div key={key} className="page-card p-5">
              <div className="flex items-center justify-between gap-2">
                <span className="text-[13px] font-medium text-muted">
                  {SUMMARY_LABELS[key] ?? key}
                </span>
                <StatusPill status={key} />
              </div>
              <div className="page-metric-value mt-3">{value}</div>
            </div>
          ))
        )}
      </section>

      <div className="flex flex-wrap items-center gap-3">
        <FilterToggleGroup
          label="事件状态筛选"
          value={status}
          options={STATUS_OPTIONS.map((item) => ({
            id: item.id,
            label: item.label,
          }))}
          onChange={(next) => {
            setStatus(next);
            setPage(1);
          }}
        />
      </div>

      {events.isLoading ? (
        <LoadingState label="加载活动…" />
      ) : events.error ? (
        <ErrorState
          message={
            events.error instanceof Error
              ? events.error.message
              : '活动加载失败'
          }
          onRetry={() => events.refetch()}
        />
      ) : items.length === 0 ? (
        <EmptyState
          title="暂无事件"
          description="筛选条件下没有记录, 或服务尚未产生事件"
        />
      ) : (
        <div className="page-card overflow-hidden">
          <div className="divide-y divide-separator">
            {items.map((event) => (
              <div
                key={event.id}
                className="flex flex-col gap-2 px-5 py-4 sm:flex-row sm:items-center sm:justify-between"
              >
                <div className="flex min-w-0 flex-1 items-center gap-3">
                  <EventIdentity
                    userId={event.user_id}
                    fallbackName={event.username}
                    accountMap={accountMap}
                  />
                  <StatusPill status={event.status} />
                </div>
                <div className="shrink-0 text-xs text-muted">
                  {formatDateTime(event.created_at)}
                  {event.error_code ? ` · ${event.error_code}` : ''}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

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

      <Modal isOpen={pruneOpen} onOpenChange={setPruneOpen}>
        <Modal.Backdrop isDismissable={false}>
          <Modal.Container placement="center" size="md">
            <Modal.Dialog>
              <Modal.CloseTrigger />
              <Modal.Header>
                <Modal.Heading>清理历史事件</Modal.Heading>
              </Modal.Header>
              <Modal.Body className="space-y-4">
                <p className="text-sm leading-6 text-muted">
                  将删除所选日期范围内的历史事件。默认范围为最早至今，此操作不可撤销。
                </p>
                <DateRangePicker
                  className="w-full"
                  aria-label="清理日期范围"
                  value={range}
                  onChange={setRange}
                  maxValue={today(getLocalTimeZone())}
                >
                  <Label>日期范围</Label>
                  <DateField.Group>
                    <DateField.InputContainer>
                      <DateField.Input slot="start">
                        {(segment) => <DateField.Segment segment={segment} />}
                      </DateField.Input>
                      <DateRangePicker.RangeSeparator />
                      <DateField.Input slot="end">
                        {(segment) => <DateField.Segment segment={segment} />}
                      </DateField.Input>
                    </DateField.InputContainer>
                    <DateField.Suffix>
                      <DateRangePicker.Trigger>
                        <DateRangePicker.TriggerIndicator />
                      </DateRangePicker.Trigger>
                    </DateField.Suffix>
                  </DateField.Group>
                  <DateRangePicker.Popover>
                    <RangeCalendar aria-label="选择清理日期范围">
                      <RangeCalendar.Header>
                        <RangeCalendar.YearPickerTrigger>
                          <RangeCalendar.YearPickerTriggerHeading />
                          <RangeCalendar.YearPickerTriggerIndicator />
                        </RangeCalendar.YearPickerTrigger>
                        <RangeCalendar.NavButton slot="previous" />
                        <RangeCalendar.NavButton slot="next" />
                      </RangeCalendar.Header>
                      <RangeCalendar.Grid>
                        <RangeCalendar.GridHeader>
                          {(day) => (
                            <RangeCalendar.HeaderCell>
                              {day}
                            </RangeCalendar.HeaderCell>
                          )}
                        </RangeCalendar.GridHeader>
                        <RangeCalendar.GridBody>
                          {(date) => <RangeCalendar.Cell date={date} />}
                        </RangeCalendar.GridBody>
                      </RangeCalendar.Grid>
                    </RangeCalendar>
                  </DateRangePicker.Popover>
                </DateRangePicker>
              </Modal.Body>
              <Modal.Footer className="flex justify-end gap-2">
                <Button variant="secondary" onPress={() => setPruneOpen(false)}>
                  取消
                </Button>
                <Button
                  variant="danger"
                  isDisabled={!range?.end || prune.isPending}
                  onPress={() => void handlePrune()}
                >
                  {prune.isPending ? '清理中…' : '确认清理'}
                </Button>
              </Modal.Footer>
            </Modal.Dialog>
          </Modal.Container>
        </Modal.Backdrop>
      </Modal>
    </div>
  );
}
