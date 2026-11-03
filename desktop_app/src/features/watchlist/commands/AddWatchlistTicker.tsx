
import { useEffect, useState, type FormEvent } from 'react';
import { Plus } from 'lucide-react';

import type { Locale, UserProfile } from '#/types.js';
import type { ToastKind } from '@/features/common/types/index.js';
import { CommandDialog } from '@/features/command-palette/components/CommandDialog.js';
import { formatError, translate } from '@/features/common/i18n/messages.js';
import { addTickerToWatchlist } from '@/features/watchlist/lib/watchlist-actions.js';



interface AddWatchlistTickerProps {
    isOpen: boolean;
    locale: Locale;
    profile: UserProfile;
    returnFocusTarget: HTMLElement | null;
    onClose: () => void;
    onNotify: (message: string, kind?: ToastKind) => void;
    onProfileChange: (profile: UserProfile) => Promise<void>;
}


export function AddWatchlistTicker({
    isOpen,
    locale,
    profile,
    returnFocusTarget,
    onClose,
    onNotify,
    onProfileChange,
}: AddWatchlistTickerProps) {
    const [ticker, setTicker] = useState('');
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const t = (key: string, values?: Record<string, string | number>) =>
        translate(locale, key, values);

    useEffect(() => {
        if (isOpen) {
            setTicker('');
            setError(null);
        }
    }, [isOpen]);

    async function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setError(null);
        setIsSaving(true);
        try {
            const result = await addTickerToWatchlist(profile, ticker);
            if (result.status === 'empty') {
                const message = t('watchlist.tickerRequired');
                setError(message);
                onNotify(message, 'error');
                return;
            }
            if (result.status === 'duplicate') {
                const message = t('watchlist.duplicateTicker');
                setError(message);
                onNotify(message, 'error');
                return;
            }

            await onProfileChange(result.profile);
            onNotify(
                t('command.watchlistAdded', { ticker: result.ticker }),
                'success',
            );
            onClose();
        } catch (requestError) {
            const message = formatError(locale, requestError);
            setError(message);
            onNotify(message, 'error');
        } finally {
            setIsSaving(false);
        }
    }

    return (
        <CommandDialog
            description={t('command.addWatchlistDescription')}
            isOpen={isOpen}
            locale={locale}
            onClose={onClose}
            returnFocusTarget={returnFocusTarget}
            title={t('command.addWatchlist')}
        >
            <form className='command-watchlist-form' onSubmit={submit}>
                <label className='form-field'>
                    <span>{t('watchlist.add')}</span>
                    <input
                        autoCapitalize='characters'
                        autoComplete='off'
                        maxLength={20}
                        onChange={(event) =>
                            setTicker(event.target.value.toUpperCase())
                        }
                        placeholder='AAPL'
                        required
                        value={ticker}
                    />
                    <small>{t('analysis.tickerHint')}</small>
                </label>
                {error && (
                    <p className='form-message error-message' role='alert'>
                        {error}
                    </p>
                )}
                <div className='command-dialog-actions'>
                    <button
                        className='button-secondary'
                        disabled={isSaving}
                        onClick={onClose}
                        type='button'
                    >
                        {t('common.cancel')}
                    </button>
                    <button
                        className='button-primary'
                        disabled={isSaving || !ticker.trim()}
                        type='submit'
                    >
                        <Plus size={16} aria-hidden='true' />
                        {isSaving
                            ? t('common.saving')
                            : t('watchlist.addAction')}
                    </button>
                </div>
            </form>
        </CommandDialog>
    );
}
