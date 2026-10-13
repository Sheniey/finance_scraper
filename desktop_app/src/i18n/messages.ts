import type { Locale } from '#/types.js';
import englishMessages from '@/i18n/locales/en.js';
import spanishMessages from '@/i18n/locales/es.js';

const messages: Record<Locale, Record<string, string>> = {
    es: spanishMessages,
    en: englishMessages,
};

export type MessageKey = keyof typeof spanishMessages;

export function translate(
    locale: Locale,
    key: MessageKey | string,
    values: Record<string, string | number> = {},
): string {
    const template = messages[locale][key] ?? messages.en[key] ?? key;
    return template.replace(/\{([^}]+)\}/g, (_match, name: string) =>
        String(values[name] ?? `{${name}}`),
    );
}

export function formatError(locale: Locale, error: unknown): string {
    const code =
        typeof error === 'object' && error !== null && 'code' in error
            ? String(error.code)
            : '';
    const keyByCode: Record<string, MessageKey> = {
        INCORRECT_CREDENTIALS: 'error.invalidCredentials',
        ACCOUNT_ALREADY_EXISTS: 'error.duplicateAccount',
        RATE_LIMIT_EXCEEDED: 'error.rateLimit',
        GOOGLE_OAUTH_NOT_CONFIGURED: 'error.googleNotConfigured',
        GOOGLE_OAUTH_FLOW_INVALID: 'error.googleSignInFailed',
        GOOGLE_OAUTH_PROVIDER_FAILED: 'error.googleSignInFailed',
        GOOGLE_ACCOUNT_NOT_CONNECTED: 'error.googleNotConnected',
        GOOGLE_SIGNIN_FAILED: 'error.googleSignInFailed',
        GOOGLE_SIGNIN_TIMEOUT: 'error.googleSignInTimeout',
        SCHEDULE_LIMIT_EXCEEDED: 'error.scheduleLimit',
        REPORT_GENERATION_FAILED: 'error.reportFailed',
        REPORT_PROVIDER_FAILED: 'error.reportFailed',
    };
    if (code && keyByCode[code]) {
        return translate(locale, keyByCode[code]);
    }
    const message =
        error instanceof Error
            ? error.message
                  .replace(
                      /^Error invoking remote method '[^']+':\s*/,
                      '',
                  )
                  .replace(/^ApiRequestError:\s*/, '')
                  .trim()
            : '';
    const keyByMessage: Record<string, MessageKey> = {
        'Incorrect email or password': 'error.invalidCredentials',
        'The Google OAuth desktop client ID must be configured':
            'error.googleNotConfigured',
        'The Google authorization flow is invalid or expired':
            'error.googleSignInFailed',
        'Google could not complete the authorization request':
            'error.googleSignInFailed',
        'Google did not grant the required sign-in permissions':
            'error.googleSignInFailed',
        'Google did not return a verified email address':
            'error.googleSignInFailed',
        'Google sign-in could not be completed. Try again.':
            'error.googleSignInFailed',
        'Google sign-in timed out. Try again.':
            'error.googleSignInTimeout',
    };
    if (keyByMessage[message]) {
        return translate(locale, keyByMessage[message]);
    }
    if (message) {
        return message;
    }
    return translate(locale, 'error.unknown');
}
