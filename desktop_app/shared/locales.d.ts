
export type SupportedLocale = 'en' | 'es' | 'fr';
export interface LocaleMetadata {
    code: SupportedLocale;
    name: string;
    intlTag: string;
}

export const supportedLocales: readonly LocaleMetadata[];

export function isSupportedLocale(value: unknown): value is SupportedLocale;
export function getLocaleMetadata(value: SupportedLocale): LocaleMetadata;
export function getPreferredLocale(
    value: string,
    fallback?: SupportedLocale,
): SupportedLocale;
