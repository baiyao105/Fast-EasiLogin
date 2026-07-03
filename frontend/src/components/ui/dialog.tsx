import { cn } from '@/lib/utils';
import { motion, AnimatePresence } from 'framer-motion';
import { motionVariants } from '@/lib/utils/motion';
import type { ReactNode } from 'react';

interface DialogProps {
  open: boolean;
  onClose: () => void;
  children: ReactNode;
}

export function Dialog({ open, onClose, children }: DialogProps) {
  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 bg-black/50 z-50"
            onClick={onClose}
          />
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
            <motion.div
              initial={motionVariants.modalOpen.initial}
              animate={motionVariants.modalOpen.animate}
              exit={motionVariants.modalOpen.exit}
              transition={motionVariants.modalOpen.transition}
              className={cn(
                'bg-surface rounded-lg shadow-strong p-6',
                'w-full max-w-md',
                'max-h-[85vh] overflow-y-auto'
              )}
              onClick={(e) => e.stopPropagation()}
            >
              {children}
            </motion.div>
          </div>
        </>
      )}
    </AnimatePresence>
  );
}

export function DialogHeader({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('flex flex-col space-y-1.5 mb-4', className)}
      {...props}
    />
  );
}

export function DialogTitle({
  className,
  ...props
}: React.HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h2
      className={cn('text-lg font-semibold', className)}
      {...props}
    />
  );
}

export function DialogContent({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={cn('', className)} {...props} />;
}

export function DialogFooter({
  className,
  ...props
}: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn('flex justify-end space-x-2 mt-4', className)}
      {...props}
    />
  );
}
