import { AlertDialog, Button, Spinner } from '@heroui/react';

export function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmLabel = '确认',
  cancelLabel = '取消',
  status = 'danger',
  loading = false,
  onConfirm,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description: string;
  confirmLabel?: string;
  cancelLabel?: string;
  status?: 'default' | 'accent' | 'success' | 'warning' | 'danger';
  loading?: boolean;
  onConfirm: () => void;
}) {
  return (
    <AlertDialog isOpen={open} onOpenChange={onOpenChange}>
      <AlertDialog.Backdrop isDismissable={false} isKeyboardDismissDisabled>
        <AlertDialog.Container placement="center" size="md">
          <AlertDialog.Dialog>
            <AlertDialog.Header>
              <AlertDialog.Icon status={status} />
              <AlertDialog.Heading>{title}</AlertDialog.Heading>
            </AlertDialog.Header>
            <AlertDialog.Body className="text-sm leading-6 text-muted">
              {description}
            </AlertDialog.Body>
            <AlertDialog.Footer>
              <Button
                variant="secondary"
                isDisabled={loading}
                onPress={() => onOpenChange(false)}
              >
                {cancelLabel}
              </Button>
              <Button
                variant={status === 'danger' ? 'danger' : 'primary'}
                isDisabled={loading}
                onPress={onConfirm}
              >
                {loading ? <Spinner size="sm" /> : null}
                {loading ? '处理中…' : confirmLabel}
              </Button>
            </AlertDialog.Footer>
          </AlertDialog.Dialog>
        </AlertDialog.Container>
      </AlertDialog.Backdrop>
    </AlertDialog>
  );
}
