import { useCallback, useEffect, useState } from 'react';

export function useAppNotifications() {
    const [toast, setToast] = useState<string | null>(null);
    const notify = useCallback((message: string) => {
        setToast(message);
    }, []);
    const dismissToast = useCallback(() => setToast(null), []);

    useEffect(() => {
        if (!toast) {
            return;
        }
        const timeout = window.setTimeout(dismissToast, 3_800);
        return () => window.clearTimeout(timeout);
    }, [dismissToast, toast]);

    return { dismissToast, notify, toast };
}
