import { Check, X } from 'lucide-react';

import type { Locale } from '#/types.js';
import { translate } from '@/i18n/messages.js';

interface ToastMessageProps {
    locale: Locale;
    message: string;
    onClose: () => void;
}

export function ToastMessage({
    locale,
    message,
    onClose,
}: ToastMessageProps) {
    return (
        <div className='toast-message' role='status' aria-live='polite'>
            <span className='toast-icon'>
                <Check size={15} aria-hidden='true' />
            </span>
            <span>{message}</span>
            <button
                aria-label={translate(locale, 'common.close')}
                className='toast-close'
                onClick={onClose}
                type='button'
            >
                <X size={14} aria-hidden='true' />
            </button>
        </div>
    );
}
