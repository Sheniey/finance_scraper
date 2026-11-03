
import type { FormEvent } from 'react';
import { Plus } from 'lucide-react';

import type { Locale } from '#/types.js';
import { LoadingSpinner } from '@/features/common/components/LoadingSpinner.js';
import { translate } from '@/features/common/i18n/messages.js';



interface PortfolioTradeFormProps {
    locale: Locale;
    action: 'BUY' | 'SELL';
    ticker: string;
    region: string;
    currency: string;
    price: string;
    quantity: string;
    tradeDate: string;
    isSaving: boolean;
    error: string | null;
    notice?: string | null;
    onActionChange: (value: 'BUY' | 'SELL') => void;
    onTickerChange: (value: string) => void;
    onRegionChange: (value: string) => void;
    onCurrencyChange: (value: string) => void;
    onPriceChange: (value: string) => void;
    onQuantityChange: (value: string) => void;
    onDateChange: (value: string) => void;
    onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}


export function PortfolioTradeForm({
    locale,
    action,
    ticker,
    region,
    currency,
    price,
    quantity,
    tradeDate,
    isSaving,
    error,
    notice,
    onActionChange,
    onTickerChange,
    onRegionChange,
    onCurrencyChange,
    onPriceChange,
    onQuantityChange,
    onDateChange,
    onSubmit,
}: PortfolioTradeFormProps) {
    const t = (key: string) => translate(locale, key);

    return (
        <form className='portfolio-form' onSubmit={onSubmit}>
            <div className='form-grid two-column'>
                <label className='form-field'>
                    <span>{t('portfolio.action')}</span>
                    <select
                        onChange={(event) =>
                            onActionChange(
                                event.target.value === 'SELL' ? 'SELL' : 'BUY',
                            )
                        }
                        value={action}
                    >
                        <option value='BUY'>{t('portfolio.buy')}</option>
                        <option value='SELL'>{t('portfolio.sell')}</option>
                    </select>
                </label>
                <label className='form-field'>
                    <span>{t('portfolio.ticker')}</span>
                    <input
                        autoCapitalize='characters'
                        maxLength={20}
                        onChange={(event) =>
                            onTickerChange(event.target.value.toUpperCase())
                        }
                        placeholder='AAPL'
                        required
                        value={ticker}
                    />
                </label>
                <label className='form-field'>
                    <span>{t('portfolio.region')}</span>
                    <input
                        maxLength={8}
                        onChange={(event) =>
                            onRegionChange(event.target.value.toUpperCase())
                        }
                        required
                        value={region}
                    />
                </label>
                <label className='form-field'>
                    <span>{t('portfolio.currency')}</span>
                    <input
                        maxLength={3}
                        onChange={(event) =>
                            onCurrencyChange(event.target.value.toUpperCase())
                        }
                        required
                        value={currency}
                    />
                </label>
                <label className='form-field'>
                    <span>{t('portfolio.quantity')}</span>
                    <input
                        min={1}
                        onChange={(event) =>
                            onQuantityChange(event.target.value)
                        }
                        required
                        step={1}
                        type='number'
                        value={quantity}
                    />
                </label>
                <label className='form-field'>
                    <span>{t('portfolio.price')}</span>
                    <input
                        min='0.000001'
                        onChange={(event) => onPriceChange(event.target.value)}
                        required
                        step='any'
                        type='number'
                        value={price}
                    />
                </label>
                <label className='form-field'>
                    <span>{t('portfolio.date')}</span>
                    <input
                        onChange={(event) => onDateChange(event.target.value)}
                        required
                        type='date'
                        value={tradeDate}
                    />
                </label>
            </div>

            {error && (
                <p className='form-message error-message' role='alert'>
                    {error}
                </p>
            )}
            {notice && (
                <p className='form-message success-message' role='status'>
                    {notice}
                </p>
            )}
            <button
                className='button-primary'
                disabled={isSaving}
                type='submit'
            >
                {isSaving ? (
                    <LoadingSpinner size={16} />
                ) : (
                    <Plus size={16} aria-hidden='true' />
                )}
                {isSaving ? t('common.saving') : t('portfolio.saveTrade')}
            </button>
        </form>
    );
}
