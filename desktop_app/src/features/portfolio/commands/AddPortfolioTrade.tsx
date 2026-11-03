
import { useEffect, useState, type FormEvent } from 'react';

import type { Locale } from '#/types.js';
import type { ToastKind } from '@/features/common/types/index.js';
import { CommandDialog } from '@/features/command-palette/components/CommandDialog.js';
import { formatError, translate } from '@/features/common/i18n/messages.js';
import { PortfolioTradeForm } from '@/features/portfolio/components/PortfolioTradeForm.js';
import {
    buildPortfolioTradeRequest,
    localDateInputValue,
} from '@/features/portfolio/lib/portfolio-actions.js';



interface AddPortfolioTradeProps {
    isOpen: boolean;
    locale: Locale;
    returnFocusTarget: HTMLElement | null;
    onClose: () => void;
    onNotify: (message: string, kind?: ToastKind) => void;
    onPortfolioChanged: () => void;
}


export function AddPortfolioTrade({
    isOpen,
    locale,
    returnFocusTarget,
    onClose,
    onNotify,
    onPortfolioChanged,
}: AddPortfolioTradeProps) {
    const [action, setAction] = useState<'BUY' | 'SELL'>('BUY');
    const [ticker, setTicker] = useState('');
    const [region, setRegion] = useState('US');
    const [currency, setCurrency] = useState('USD');
    const [price, setPrice] = useState('');
    const [quantity, setQuantity] = useState('1');
    const [tradeDate, setTradeDate] = useState(localDateInputValue);
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const t = (key: string) => translate(locale, key);

    useEffect(() => {
        if (isOpen) {
            setAction('BUY');
            setTicker('');
            setRegion('US');
            setCurrency('USD');
            setPrice('');
            setQuantity('1');
            setTradeDate(localDateInputValue());
            setError(null);
        }
    }, [isOpen]);

    async function submit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setError(null);

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
            await window.desktopApi.createPortfolioTrade(validation.request);
            onPortfolioChanged();
            onNotify(t('portfolio.saved'), 'success');
            onClose();
        } catch (saveError) {
            const message = formatError(locale, saveError);
            setError(message);
            onNotify(message, 'error');
        } finally {
            setIsSaving(false);
        }
    }

    return (
        <CommandDialog
            description={t('command.addPortfolioTradeDescription')}
            isOpen={isOpen}
            locale={locale}
            onClose={onClose}
            returnFocusTarget={returnFocusTarget}
            title={t('command.addPortfolioTrade')}
        >
            <PortfolioTradeForm
                action={action}
                currency={currency}
                error={error}
                isSaving={isSaving}
                locale={locale}
                onActionChange={setAction}
                onCurrencyChange={setCurrency}
                onDateChange={setTradeDate}
                onPriceChange={setPrice}
                onQuantityChange={setQuantity}
                onRegionChange={setRegion}
                onSubmit={submit}
                onTickerChange={setTicker}
                price={price}
                quantity={quantity}
                region={region}
                ticker={ticker}
                tradeDate={tradeDate}
            />
        </CommandDialog>
    );
}
