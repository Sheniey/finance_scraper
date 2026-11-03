
import { useCallback, useRef, useState } from 'react';

import type {
    ToastKind,
    ToastNotification,
} from '@/features/common/types/index.js';

export function useAppNotifications() {
    const [toasts, setToasts] = useState<ToastNotification[]>([]);
    const nextId = useRef(0);
    const notify = useCallback((message: string, kind: ToastKind = 'info') => {
        const id = ++nextId.current;
        setToasts((current) =>
            [...current, { id, message, kind }].slice(-4),
        );
    }, []);
    const dismissToast = useCallback((id: number) => {
        setToasts((current) => current.filter((toast) => toast.id !== id));
    }, []);

    return { dismissToast, notify, toasts };
}
