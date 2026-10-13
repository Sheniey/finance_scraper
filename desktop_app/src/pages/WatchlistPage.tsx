import { useMemo, useState, type FormEvent } from 'react';
import { ArrowUpRight, Plus, X } from 'lucide-react';

import type { Locale, UserProfile, WatchlistItem } from '#/types.js';
import { formatError, translate } from '@/i18n/messages.js';

interface WatchlistPageProps {
    locale: Locale;
    profile: UserProfile;
    onProfileChange: (profile: UserProfile) => void;
    onNavigate: (view: 'schedules') => void;
}

export function WatchlistPage({
    locale,
    profile,
    onProfileChange,
    onNavigate,
}: WatchlistPageProps) {
    const t = (key: string) => translate(locale, key);
    const [ticker, setTicker] = useState('');
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const items = useMemo(
        () => profile.watchlist.filter((item): item is WatchlistItem => Boolean(item)),
        [profile.watchlist],
    );

    async function saveWatchlist(next: WatchlistItem[]) {
        setIsSaving(true);
        setError(null);
        try {
            const updated = await window.desktopApi.updateProfile({
                ...profile,
                watchlist: next,
            });
            onProfileChange(updated);
        } catch (requestError) {
            setError(formatError(locale, requestError));
        } finally {
            setIsSaving(false);
        }
    }

    async function addTicker(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        const normalized = ticker.trim().toUpperCase();
        if (!normalized) {
            return;
        }
        const alreadyExists = items.some((item) => item.ticker === normalized);
        if (alreadyExists) {
            setError(
                locale === 'es'
                    ? 'Ese ticker ya está en tu watchlist.'
                    : 'That ticker is already on your watchlist.',
            );
            return;
        }
        await saveWatchlist([
            ...items,
            {
                ticker: normalized,
                region: 'US',
                mode: 'custom',
                llm_explanation: false,
                charts: true,
                horizon: 15,
                enabled: true,
            },
        ]);
        setTicker('');
    }

    return (
        <div className='page-stack'>
            <header className='page-heading split-heading'>
                <div>
                    <p className='eyebrow dark'>
                        <span className='signal-mark' />
                        {t('nav.watchlist')}
                    </p>
                    <h1>{t('watchlist.title')}</h1>
                    <p>{t('watchlist.copy')}</p>
                </div>
                <button
                    className='button-secondary'
                    onClick={() => onNavigate('schedules')}
                    type='button'
                >
                    {t('nav.schedules')}
                    <ArrowUpRight size={15} aria-hidden='true' />
                </button>
            </header>

            <section className='content-panel watchlist-panel'>
                <form className='watchlist-add-form' onSubmit={addTicker}>
                    <label className='form-field'>
                        <span>{t('watchlist.add')}</span>
                        <input
                            autoCapitalize='characters'
                            maxLength={20}
                            onChange={(event) =>
                                setTicker(event.target.value.toUpperCase())
                            }
                            placeholder='AAPL'
                            value={ticker}
                        />
                    </label>
                    <button
                        className='button-primary'
                        disabled={isSaving || !ticker.trim()}
                        type='submit'
                    >
                        <Plus size={16} aria-hidden='true' />
                        {t('watchlist.addAction')}
                    </button>
                </form>
                {error && (
                    <p className='form-message error-message' role='alert'>
                        {error}
                    </p>
                )}
                {items.length > 0 ? (
                    <ul className='watchlist-items'>
                        {items.map((item) => (
                            <li key={`${item.ticker}-${item.region}`}>
                                <span className='ticker-monogram'>
                                    {item.ticker.slice(0, 2)}
                                </span>
                                <span className='watchlist-item-copy'>
                                    <strong>{item.ticker}</strong>
                                    <small>
                                        {item.region} · {item.mode}
                                    </small>
                                </span>
                                <span className='watchlist-item-state'>
                                    {item.enabled ? t('common.enabled') : t('common.paused')}
                                </span>
                                <button
                                    aria-label={`${t('watchlist.remove')} ${item.ticker}`}
                                    className='icon-action danger'
                                    disabled={isSaving}
                                    onClick={() =>
                                        void saveWatchlist(
                                            items.filter(
                                                (entry) =>
                                                    entry.ticker !== item.ticker,
                                            ),
                                        )
                                    }
                                    type='button'
                                >
                                    <X size={15} aria-hidden='true' />
                                </button>
                            </li>
                        ))}
                    </ul>
                ) : (
                    <div className='empty-state'>
                        <span className='empty-mark'>
                            <Plus size={19} aria-hidden='true' />
                        </span>
                        <strong>{t('watchlist.empty')}</strong>
                        <p>{t('watchlist.copy')}</p>
                    </div>
                )}
            </section>
        </div>
    );
}
