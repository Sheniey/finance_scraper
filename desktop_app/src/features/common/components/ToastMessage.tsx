
import { useEffect } from 'react';
import { motion } from 'motion/react';
import { AlertCircle, Check, Info, X } from 'lucide-react';

import type { Locale } from '#/types.js';
import { translate } from '@/features/common/i18n/messages.js';
import type { ToastNotification } from '@/features/common/types/index.js';



interface ToastMessageProps {
    locale: Locale;
    notification: ToastNotification;
    onDismiss: (id: number) => void;
}


export function ToastMessage({
    locale,
    notification,
    onDismiss,
}: ToastMessageProps) {
    useEffect(() => {
        const timeout = window.setTimeout(
            () => onDismiss(notification.id),
            3_800,
        );
        return () => window.clearTimeout(timeout);
    }, [notification.id, onDismiss]);

    const Icon =
        notification.kind === 'error'
            ? AlertCircle
            : notification.kind === 'success'
              ? Check
              : Info;

    return (
        <motion.div
            animate={{ opacity: 1, scale: 1, y: 0 }}
            className={`toast-message toast-message-${notification.kind}`}
            exit={{ opacity: 0, scale: 0.96, y: 14 }}
            initial={{ opacity: 0, scale: 0.96, y: 14 }}
            layout
            role={notification.kind === 'error' ? 'alert' : 'status'}
            transition={{ type: 'spring', stiffness: 420, damping: 32 }}
        >
            <span className='toast-icon'>
                <Icon size={15} aria-hidden='true' />
            </span>
            <span className='toast-copy'>{notification.message}</span>
            <button
                aria-label={translate(locale, 'common.close')}
                className='toast-close'
                onClick={() => onDismiss(notification.id)}
                type='button'
            >
                <X size={14} aria-hidden='true' />
            </button>
        </motion.div>
    );
}
