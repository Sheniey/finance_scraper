
import { useEffect, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { Check, Copy } from 'lucide-react';

import type { Locale } from '#/types.js';
import type { ToastKind } from '@/features/common/types/index.js';
import { formatError, translate } from '@/features/common/i18n/messages.js';



interface CopyTickerButtonProps {
    locale: Locale;
    ticker: string;
    onNotify: (message: string, kind?: ToastKind) => void;
}


export function CopyTickerButton({
    locale,
    ticker,
    onNotify,
}: CopyTickerButtonProps) {
    const [copied, setCopied] = useState(false);
    const resetTimeout = useRef<number | null>(null);

    useEffect(
        () => () => {
            if (resetTimeout.current !== null) {
                window.clearTimeout(resetTimeout.current);
            }
        },
        [],
    );

    async function copyTicker() {
        try {
            if (!navigator.clipboard?.writeText) {
                throw new Error(translate(locale, 'error.clipboardUnavailable'));
            }
            await navigator.clipboard.writeText(ticker);
            setCopied(true);
            onNotify(
                translate(locale, 'watchlist.tickerCopied', { ticker }),
                'success',
            );
            if (resetTimeout.current !== null) {
                window.clearTimeout(resetTimeout.current);
            }
            resetTimeout.current = window.setTimeout(
                () => setCopied(false),
                1_600,
            );
        } catch (copyError) {
            onNotify(formatError(locale, copyError), 'error');
        }
    }

    return (
        <motion.button
            aria-label={translate(locale, 'watchlist.copyTicker', { ticker })}
            className='icon-action watchlist-copy-button'
            onClick={() => void copyTicker()}
            title={translate(locale, 'watchlist.copyTicker', { ticker })}
            type='button'
            whileTap={{ scale: 0.88 }}
        >
            <AnimatePresence initial={false} mode='wait'>
                {copied ? (
                    <motion.span
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.72 }}
                        initial={{ opacity: 0, scale: 0.72 }}
                        key='copied'
                        transition={{ duration: 0.12 }}
                    >
                        <Check size={15} aria-hidden='true' />
                    </motion.span>
                ) : (
                    <motion.span
                        animate={{ opacity: 1, scale: 1 }}
                        exit={{ opacity: 0, scale: 0.72 }}
                        initial={{ opacity: 0, scale: 0.72 }}
                        key='copy'
                        transition={{ duration: 0.12 }}
                    >
                        <Copy size={15} aria-hidden='true' />
                    </motion.span>
                )}
            </AnimatePresence>
        </motion.button>
    );
}
