
import { AnimatePresence, motion } from 'motion/react';

import type { Locale } from '#/types.js';
import type {
    ToastKind,
    ToastNotification,
} from '@/features/common/types/index.js';
import { ToastMessage } from '@/features/common/components/ToastMessage.js';
import { translate } from '@/features/common/i18n/messages.js';



interface ToastStackProps {
    locale: Locale;
    notifications: ToastNotification[];
    onDismiss: (id: number) => void;
}


export function ToastStack({
    locale,
    notifications,
    onDismiss,
}: ToastStackProps) {
    return (
        <motion.div
            aria-label={translate(locale, 'notifications.title')}
            className='toast-stack'
            layout
            role='region'
        >
            <AnimatePresence initial={false}>
                {notifications.map((notification) => (
                    <ToastMessage
                        key={notification.id}
                        locale={locale}
                        notification={notification}
                        onDismiss={onDismiss}
                    />
                ))}
            </AnimatePresence>
        </motion.div>
    );
}
