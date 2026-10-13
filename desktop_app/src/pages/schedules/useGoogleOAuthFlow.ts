import { useEffect, useState } from 'react';
import type { Dispatch, SetStateAction } from 'react';

import type { GoogleOAuthFlow, Locale } from '#/types.js';
import { formatError, translate } from '@/i18n/messages.js';

interface UseGoogleOAuthFlowOptions {
    locale: Locale;
    onRefresh: () => Promise<void>;
    onNotify: (message: string) => void;
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
                    onNotify(t('schedules.oauthDone'));
                } else if (status.status === 'failed') {
                    setFlowId(null);
                    setError(t('schedules.oauthFailed'));
                }
            } catch (flowError) {
                if (isMounted) {
                    setFlowId(null);
                    setError(formatError(locale, flowError));
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
            setError(formatError(locale, connectError));
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
            setError(formatError(locale, disconnectError));
        }
    }

    return {
        connectGoogle,
        disconnectGoogle,
        flowStatus,
        isConnecting,
    };
}
