
import { useEffect, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';

import type { GoogleOAuthFlow, Locale } from '#/types.js';
import type { ToastKind } from '@/features/common/types/index.js';
import { formatError, translate } from '@/features/common/i18n/messages.js';

interface UseGoogleOAuthFlowOptions {
    locale: Locale;
    onRefresh: () => Promise<void>;
    onNotify: (message: string, kind?: ToastKind) => void;
    setError: Dispatch<SetStateAction<string | null>>;
}

export function useGoogleOAuthFlow({
    locale,
    onRefresh,
    onNotify,
    setError,
}: UseGoogleOAuthFlowOptions) {
    const [flowId, setFlowId] = useState<string | null>(null);
    const [flowStatus, setFlowStatus] = useState<GoogleOAuthFlow | null>(null);
    const [isConnecting, setIsConnecting] = useState(false);
    const t = (key: string) => translate(locale, key);

    useEffect(() => {
        if (!flowId) {
            return;
        }
        let isMounted = true;
        const checkFlow = async () => {
            try {
                const status = await window.desktopApi.getGoogleFlow(flowId);
                if (!isMounted) {
                    return;
                }
                setFlowStatus(status);
                if (status.status === 'completed') {
                    setFlowId(null);
                    await onRefresh();
                    onNotify(t('schedules.oauthDone'), 'success');
                } else if (status.status === 'failed') {
                    setFlowId(null);
                    const message = t('schedules.oauthFailed');
                    setError(message);
                    onNotify(message, 'error');
                }
            } catch (flowError) {
                if (isMounted) {
                    setFlowId(null);
                    const message = formatError(locale, flowError);
                    setError(message);
                    onNotify(message, 'error');
                }
            }
        };

        void checkFlow();
        const timer = window.setInterval(() => void checkFlow(), 1_500);
        return () => {
            isMounted = false;
            window.clearInterval(timer);
        };
    }, [flowId, locale, onNotify, onRefresh, setError]);

    async function connectGoogle() {
        setIsConnecting(true);
        setError(null);
        try {
            const flow = await window.desktopApi.connectGoogle();
            setFlowId(flow.flow_id);
            setFlowStatus({
                flow_id: flow.flow_id,
                status: 'pending',
                email: null,
                error: null,
            });
        } catch (connectError) {
            const message = formatError(locale, connectError);
            setError(message);
            onNotify(message, 'error');
        } finally {
            setIsConnecting(false);
        }
    }

    async function disconnectGoogle() {
        if (!window.confirm(t('schedules.confirmDisconnect'))) {
            return;
        }
        setError(null);
        try {
            await window.desktopApi.disconnectGoogle();
            await onRefresh();
        } catch (disconnectError) {
            const message = formatError(locale, disconnectError);
            setError(message);
            onNotify(message, 'error');
        }
    }

    return {
        connectGoogle,
        disconnectGoogle,
        flowStatus,
        isConnecting,
    };
}
