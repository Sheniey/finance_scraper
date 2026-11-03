
import type { Locale } from '#/types.js';

export type { Locale } from '#/types.js';

export interface LocaleOption {
    locale: Locale;
    code: string;
    name: string;
}

export type ToastKind = 'success' | 'error' | 'info';

export interface ToastNotification {
    id: number;
    message: string;
    kind: ToastKind;
}
