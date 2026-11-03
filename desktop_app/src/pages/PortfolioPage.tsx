
import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { BriefcaseBusiness } from 'lucide-react';

import type {
    Locale,
    PortfolioAction,
    PortfolioHolding,
} from '#/types.js';
import {
    formatError,
    getIntlLocale,
    translate,
} from '@/features/common/i18n/messages.js';
import PageTitle from '@/features/common/components/PageTitle.js';
import { PortfolioTradeForm } from '@/features/portfolio/components/PortfolioTradeForm.js';
import {
    buildPortfolioTradeRequest,
    localDateInputValue,
} from '@/features/portfolio/lib/portfolio-actions.js';
import type { PortfolioTradeRow } from '@/features/portfolio/types/index.js';



function netShares(actions: PortfolioAction[]): number {
    return actions.reduce(
        (total, action) =>
            total + action.quantity * (action.action === 'BUY' ? 1 : -1),
        0,
    );
}

interface PortfolioPageProps {
    locale: Locale;
    refreshToken: number;
}


export function PortfolioPage({ locale, refreshToken }: PortfolioPageProps) {
    const [portfolio, setPortfolio] = useState<PortfolioHolding[]>([]);
    const [action, setAction] = useState<'BUY' | 'SELL'>('BUY');
    const [ticker, setTicker] = useState('');
    const [region, setRegion] = useState('US');
    const [currency, setCurrency] = useState('USD');
    const [price, setPrice] = useState('');
    const [quantity, setQuantity] = useState('1');
    const [tradeDate, setTradeDate] = useState(localDateInputValue);
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [notice, setNotice] = useState<string | null>(null);
    const t = (key: string, values?: Record<string, string | number>) =>
        translate(locale, key, values);

    useEffect(() => {
        let isCurrent = true;
        void window.desktopApi
            .getPortfolio()
            .then((response) => {
                if (isCurrent) {
                    setPortfolio(response.portfolio);
                }
            })
            .catch((loadError: unknown) => {
                if (isCurrent) {
                    setError(formatError(locale, loadError));
                }
            })
            .finally(() => {
                if (isCurrent) {
                    setIsLoading(false);
                }
            });
        return () => {
            isCurrent = false;
        };
    }, [locale, refreshToken]);

    const trades = useMemo<PortfolioTradeRow[]>(() => {
        const rows = portfolio.flatMap((holding) =>
            holding.actions.map((trade, index) => ({
                holding,
                action: trade,
                key: `${holding.ticker}-${holding.region}-${trade.date}-${index}`,
            })),
        );
        return rows.sort((left, right) =>
            right.action.date.localeCompare(left.action.date),
        );
    }, [portfolio]);
    const openPositions = portfolio.filter(
        (holding) => netShares(holding.actions) !== 0,
    ).length;

    async function addTrade(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setError(null);
        setNotice(null);

        const validation = buildPortfolioTradeRequest({
            action,
            ticker,
            region,
            currency,
            price,
            quantity,
            date: tradeDate,
        });
        if (!validation.ok) {
            setError(t(validation.errorKey));
            return;
        }

        setIsSaving(true);
        try {
            const response =
                await window.desktopApi.createPortfolioTrade(validation.request);
            setPortfolio(response.portfolio);
            setTicker('');
            setPrice('');
            setQuantity('1');
            setTradeDate(localDateInputValue());
            setNotice(t('portfolio.saved'));
        } catch (saveError) {
            setError(formatError(locale, saveError));
        } finally {
            setIsSaving(false);
        }
    }

    return (
        <div className='page-stack'>
            <header className='page-heading'>
                <PageTitle
                    sectionName={t('nav.portfolio')}
                    title={t('portfolio.title')}
                    copy={t('portfolio.copy')}
                />
            </header>

            <div className='portfolio-summary-grid'>
                <article className='content-panel portfolio-summary-card'>
                    <span className='portfolio-summary-icon'>
                        <BriefcaseBusiness size={18} aria-hidden='true' />
                    </span>
                    <p>{t('portfolio.positions')}</p>
                    <strong>{openPositions}</strong>
                    <small>{t('portfolio.positionsHint')}</small>
                </article>
                <article className='content-panel portfolio-summary-card'>
                    <span className='portfolio-summary-icon accent'>
                        <span aria-hidden='true'>Σ</span>
                    </span>
                    <p>{t('portfolio.tradesCount')}</p>
                    <strong>{trades.length}</strong>
                    <small>{t('portfolio.aiContext')}</small>
                </article>
            </div>

            <div className='portfolio-layout'>
                <section className='content-panel portfolio-form-panel'>
                    <div className='panel-heading-row'>
                        <div>
                            <p className='field-kicker'>
                                {t('portfolio.newTrade')}
                            </p>
                            <h2>{t('portfolio.recordTrade')}</h2>
                        </div>
                    </div>
                    <PortfolioTradeForm
                        action={action}
                        currency={currency}
                        error={error}
                        isSaving={isSaving}
                        locale={locale}
                        notice={notice}
                        onActionChange={setAction}
                        onCurrencyChange={setCurrency}
                        onDateChange={setTradeDate}
                        onPriceChange={setPrice}
                        onQuantityChange={setQuantity}
                        onRegionChange={setRegion}
                        onSubmit={addTrade}
                        onTickerChange={setTicker}
                        price={price}
                        quantity={quantity}
                        region={region}
                        ticker={ticker}
                        tradeDate={tradeDate}
                    />
                </section>

                <section className='content-panel portfolio-history-panel'>
                    <div className='panel-heading-row'>
                        <div>
                            <p className='field-kicker'>
                                {t('portfolio.activity')}
                            </p>
                            <h2>{t('portfolio.tradeHistory')}</h2>
                        </div>
                        {isLoading && (
                            <span className='subtle-loading'>
                                {t('common.loading')}
                            </span>
                        )}
                    </div>
                    {trades.length > 0 ? (
                        <div className='portfolio-table-scroll'>
                            <table className='portfolio-table'>
                                <thead>
                                    <tr>
                                        <th>{t('portfolio.date')}</th>
                                        <th>{t('portfolio.ticker')}</th>
                                        <th>{t('portfolio.action')}</th>
                                        <th>{t('portfolio.quantity')}</th>
                                        <th>{t('portfolio.price')}</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {trades.map(({ action: trade, holding, key }) => (
                                        <tr key={key}>
                                            <td>{trade.date}</td>
                                            <td>
                                                <strong>{holding.ticker}</strong>
                                                <small>{holding.region}</small>
                                            </td>
                                            <td>
                                                <span
                                                    className={`portfolio-trade-action ${trade.action.toLowerCase()}`}
                                                >
                                                    {t(
                                                        trade.action === 'BUY'
                                                            ? 'portfolio.buy'
                                                            : 'portfolio.sell',
                                                    )}
                                                </span>
                                            </td>
                                            <td>{trade.quantity}</td>
                                            <td>
                                                {holding.currency}{' '}
                                                {trade.price.toLocaleString(
                                                    getIntlLocale(locale),
                                                    {
                                                        minimumFractionDigits: 2,
                                                        maximumFractionDigits: 4,
                                                    },
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    ) : (
                        <div className='empty-state portfolio-empty-state'>
                            <span className='empty-mark'>
                                <BriefcaseBusiness size={18} aria-hidden='true' />
                            </span>
                            <strong>{t('portfolio.empty')}</strong>
                            <p>{t('portfolio.emptyCopy')}</p>
                        </div>
                    )}
                </section>
            </div>
        </div>
    );
}
