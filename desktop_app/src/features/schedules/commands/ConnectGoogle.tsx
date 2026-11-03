
import { useEffect, useState } from 'react';

import type { GoogleAccountStatus, Locale } from '#/types.js';
import type { ToastKind } from '@/features/common/types/index.js';
import { CommandDialog } from '@/features/command-palette/components/CommandDialog.js';
import { GoogleConnectionCard } from '@/features/schedules/components/GoogleConnectionCard.js';
import { useGoogleOAuthFlow } from '@/features/schedules/hooks/useGoogleOAuthFlow.js';
import { translate } from '@/features/common/i18n/messages.js';



interface ConnectGoogleProps {
    isOpen: boolean;
    locale: Locale;
    googleStatus: GoogleAccountStatus | null;
    returnFocusTarget: HTMLElement | null;
    onClose: () => void;
    onNotify: (message: string, kind?: ToastKind) => void;
    onRefresh: () => Promise<void>;
}


export function ConnectGoogle({
    isOpen,
    locale,
    googleStatus,
    returnFocusTarget,
    onClose,
    onNotify,
    onRefresh,
}: ConnectGoogleProps) {
    const [error, setError] = useState<string | null>(null);
    const t = (key: string) => translate(locale, key);
    const oauth = useGoogleOAuthFlow({
        locale,
        onRefresh,
        onNotify,
        setError,
    });

    useEffect(() => {
        if (isOpen) {
            setError(null);
        }
    }, [isOpen]);

    return (
        <CommandDialog
            description={t('command.connectGoogleDescription')}
            isOpen={isOpen}
            locale={locale}
            onClose={onClose}
            returnFocusTarget={returnFocusTarget}
            title={t('command.connectGoogle')}
        >
            {error && (
                <p className='form-message error-message' role='alert'>
                    {error}
                </p>
            )}
            <GoogleConnectionCard
                flowStatus={oauth.flowStatus}
                googleStatus={googleStatus}
                isConnecting={oauth.isConnecting}
                locale={locale}
                onConnect={() => void oauth.connectGoogle()}
                onDisconnect={() => void oauth.disconnectGoogle()}
            />
        </CommandDialog>
    );
}
