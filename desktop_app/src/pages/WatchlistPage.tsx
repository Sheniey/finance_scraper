
import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react';
import { ArrowUpRight, Copy, MoreHorizontal, Plus, Trash2 } from 'lucide-react';

import type { Locale, UserProfile, WatchlistItem } from '#/types.js';
import { formatError, translate } from '@/features/common/i18n/messages.js';
import PageTitle from '@/features/common/components/PageTitle.js';
import type { ToastKind } from '@/features/common/types/index.js';
import { CopyTickerButton } from '@/features/watchlist/components/CopyTickerButton.js';
import { addTickerToWatchlist } from '@/features/watchlist/lib/watchlist-actions.js';
import { ResourceContextMenu } from '@/features/command-palette/components/ResourceContextMenu.js';
import type { ResourceContextAction } from '@/features/command-palette/types/index.js';



interface WatchlistPageProps {
    locale: Locale;
    profile: UserProfile;
    onProfileChange: (profile: UserProfile) => void;
    onNotify: (message: string, kind?: ToastKind) => void;
    onNavigate: (view: 'schedules') => void;
}


export function WatchlistPage({
    locale,
    profile,
    onProfileChange,
    onNotify,
    onNavigate,
}: WatchlistPageProps) {
    const t = (key: string, values?: Record<string, string | number>) =>
        translate(locale, key, values);
    const [ticker, setTicker] = useState('');
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [contextMenu, setContextMenu] = useState<{
        ticker: string;
        x: number;
        y: number;
        focusFirstItem: boolean;
        returnFocusTarget: HTMLElement | null;
    } | null>(null);
    const hoverOpenTimer = useRef<number | null>(null);
    const hoverCloseTimer = useRef<number | null>(null);
    const items = useMemo(
        () => profile.watchlist.filter((item): item is WatchlistItem => Boolean(item)),
        [profile.watchlist],
    );
    const contextItem = items.find(
        (item) => item.ticker === contextMenu?.ticker,
    );

    function clearContextMenuTimers() {
        if (hoverOpenTimer.current !== null) {
            window.clearTimeout(hoverOpenTimer.current);
            hoverOpenTimer.current = null;
        }
        if (hoverCloseTimer.current !== null) {
            window.clearTimeout(hoverCloseTimer.current);
            hoverCloseTimer.current = null;
        }
    }

    function openContextMenu(
        itemTicker: string,
        x: number,
        y: number,
        focusFirstItem = false,
        returnFocusTarget: HTMLElement | null = null,
    ) {
        clearContextMenuTimers();
        setContextMenu({
            ticker: itemTicker,
            x,
            y,
            focusFirstItem,
            returnFocusTarget,
        });
    }

    function closeContextMenu() {
        clearContextMenuTimers();
        setContextMenu(null);
    }

    function scheduleContextMenuClose() {
        if (hoverCloseTimer.current !== null) {
            window.clearTimeout(hoverCloseTimer.current);
        }
        hoverCloseTimer.current = window.setTimeout(
            () => setContextMenu(null),
            160,
        );
    }

    useEffect(
        () => () => {
            clearContextMenuTimers();
        },
        [],
    );

    async function copyTicker(itemTicker: string) {
        try {
            if (!navigator.clipboard?.writeText) {
                throw new Error(t('error.clipboardUnavailable'));
            }
            await navigator.clipboard.writeText(itemTicker);
            onNotify(
                t('watchlist.tickerCopied', { ticker: itemTicker }),
                'success',
            );
        } catch (copyError) {
            onNotify(formatError(locale, copyError), 'error');
        }
    }

    const contextActions: ResourceContextAction[] = contextItem
        ? [
              {
                  id: 'copy',
                  label: t('watchlist.copyTicker', {
                      ticker: contextItem.ticker,
                  }),
                  icon: Copy,
                  onSelect: () => copyTicker(contextItem.ticker),
              },
              {
                  id: 'remove',
                  label: t('watchlist.remove'),
                  icon: Trash2,
                  danger: true,
                  separatorBefore: true,
                  onSelect: async () => {
                      if (
                          window.confirm(
                              t('watchlist.confirmRemove', {
                                  ticker: contextItem.ticker,
                              }),
                          )
                      ) {
                          await saveWatchlist(
                              items.filter(
                                  (item) =>
                                      item.ticker !== contextItem.ticker,
                              ),
                          );
                      }
                  },
              },
          ]
        : [];

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
            const message = formatError(locale, requestError);
            setError(message);
            onNotify(message, 'error');
        } finally {
            setIsSaving(false);
        }
    }

    async function addTicker(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setError(null);
        setIsSaving(true);
        try {
            const result = await addTickerToWatchlist(profile, ticker);
            if (result.status === 'empty') {
                setError(t('watchlist.tickerRequired'));
                return;
            }
            if (result.status === 'duplicate') {
                const message = t('watchlist.duplicateTicker');
                setError(message);
                onNotify(message, 'error');
                return;
            }
            onProfileChange(result.profile);
            setTicker('');
        } catch (requestError) {
            const message = formatError(locale, requestError);
            setError(message);
            onNotify(message, 'error');
        } finally {
            setIsSaving(false);
        }
    }

    return (
        <div className='page-stack'>
            <header className='page-heading'>
                <PageTitle
                    sectionName={t('nav.watchlist')}
                    title={t('watchlist.title')}
                    copy={t('watchlist.copy')}
                />
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
                            <li
                                key={`${item.ticker}-${item.region}`}
                                tabIndex={-1}
                                onContextMenu={(event) => {
                                    event.preventDefault();
                                    openContextMenu(
                                        item.ticker,
                                        event.clientX + 8,
                                        event.clientY + 8,
                                        true,
                                        event.currentTarget,
                                    );
                                }}
                                onMouseEnter={(event) => {
                                    if (contextMenu?.ticker === item.ticker) {
                                        clearContextMenuTimers();
                                        return;
                                    }
                                    const x = event.clientX + 10;
                                    const y = event.clientY + 10;
                                    if (hoverOpenTimer.current !== null) {
                                        window.clearTimeout(
                                            hoverOpenTimer.current,
                                        );
                                    }
                                    hoverOpenTimer.current =
                                        window.setTimeout(
                                            () =>
                                                openContextMenu(
                                                    item.ticker,
                                                    x,
                                                    y,
                                                ),
                                            320,
                                        );
                                }}
                                onMouseLeave={(event) => {
                                    if (
                                        event.relatedTarget instanceof
                                            HTMLElement &&
                                        event.relatedTarget.closest(
                                            '[data-resource-context-menu]',
                                        )
                                    ) {
                                        clearContextMenuTimers();
                                        return;
                                    }
                                    if (hoverOpenTimer.current !== null) {
                                        window.clearTimeout(
                                            hoverOpenTimer.current,
                                        );
                                        hoverOpenTimer.current = null;
                                    }
                                    scheduleContextMenuClose();
                                }}
                            >
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
                                <CopyTickerButton
                                    locale={locale}
                                    onNotify={onNotify}
                                    ticker={item.ticker}
                                />
                                <button
                                    aria-expanded={
                                        contextMenu?.ticker === item.ticker
                                    }
                                    aria-haspopup='menu'
                                    aria-label={`${t('reports.moreActions')}: ${item.ticker}`}
                                    className='icon-action watchlist-more-button'
                                    data-resource-context-trigger=''
                                    disabled={isSaving}
                                    onClick={(event) => {
                                        const button = event.currentTarget;
                                        if (contextMenu?.ticker === item.ticker) {
                                            setContextMenu((current) =>
                                                current
                                                    ? {
                                                          ...current,
                                                          focusFirstItem: true,
                                                          returnFocusTarget:
                                                              button,
                                                      }
                                                    : current,
                                            );
                                            return;
                                        }
                                        const rect =
                                            button.getBoundingClientRect();
                                        openContextMenu(
                                            item.ticker,
                                            rect.right - 220,
                                            rect.bottom + 5,
                                            true,
                                            button,
                                        );
                                    }}
                                    title={t('reports.moreActions')}
                                    type='button'
                                >
                                    <MoreHorizontal
                                        size={17}
                                        aria-hidden='true'
                                    />
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
            <ResourceContextMenu
                actions={contextActions}
                focusFirstItem={contextMenu?.focusFirstItem ?? false}
                isOpen={contextMenu !== null && contextItem !== undefined}
                label={
                    contextItem
                        ? `${t('reports.moreActions')}: ${contextItem.ticker}`
                        : t('reports.moreActions')
                }
                onClose={closeContextMenu}
                onMouseEnter={clearContextMenuTimers}
                onMouseLeave={scheduleContextMenuClose}
                position={{
                    x: contextMenu?.x ?? 8,
                    y: contextMenu?.y ?? 8,
                }}
                returnFocusTarget={contextMenu?.returnFocusTarget ?? null}
            />
        </div>
    );
}
