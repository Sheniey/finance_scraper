
export const supportedLocales = Object.freeze([
    Object.freeze({ code: 'en', name: 'English', intlTag: 'en-US' }),
    Object.freeze({ code: 'es', name: 'Español', intlTag: 'es-MX' }),
    Object.freeze({ code: 'fr', name: 'Français', intlTag: 'fr-FR' }),
]);

export function isSupportedLocale(value) {
    return (
        typeof value === 'string' &&
        supportedLocales.some(({ code }) => code === value)
    );
}

export function getLocaleMetadata(value) {
    const locale = supportedLocales.find(({ code }) => code === value);
    if (!locale) {
        throw new RangeError(`Unsupported locale: ${value}`);
    }
    return locale;
}

export function getPreferredLocale(value, fallback = 'es') {
    const language =
        typeof value === 'string'
            ? value.toLowerCase().replace('_', '-').split('-')[0]
            : '';
    return isSupportedLocale(language) ? language : fallback;
}
