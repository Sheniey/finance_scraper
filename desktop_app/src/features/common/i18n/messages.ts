
import type { Locale } from '#/types.js';
import {
    getLocaleMetadata,
    getPreferredLocale,
    supportedLocales,
} from '#/locales.js';
import type { LocaleOption } from '@/features/common/types/index.js';
import aiProvidersEn from '@/features/ai-providers/locales/en.js';
import analysisEn from '@/features/analysis/locales/en.js';
import applicationEn from '@/features/application/locales/en.js';
import authEn from '@/features/auth/locales/en.js';
import commandPaletteEn from '@/features/command-palette/locales/en.js';
import commonEn from '@/features/common/locales/en.js';
import portfolioEn from '@/features/portfolio/locales/en.js';
import reportsEn from '@/features/reports/locales/en.js';
import schedulesEn from '@/features/schedules/locales/en.js';
import settingsEn from '@/features/settings/locales/en.js';
import watchlistEn from '@/features/watchlist/locales/en.js';
import workspaceEn from '@/features/workspace/locales/en.js';

const englishMessages = {
    ...commonEn,
    ...applicationEn,
    ...authEn,
    ...aiProvidersEn,
    ...analysisEn,
    ...commandPaletteEn,
    ...portfolioEn,
    ...reportsEn,
    ...schedulesEn,
    ...settingsEn,
    ...watchlistEn,
    ...workspaceEn,
};

export type MessageKey = keyof typeof englishMessages;

type MessageCatalog = Record<MessageKey, string> & Record<string, string>;

const localeModules = import.meta.glob<Record<string, string>>(
    '../../*/locales/*.ts',
    { eager: true, import: 'default' },
);
const englishLocaleModules = Object.entries(localeModules).filter(([path]) =>
    path.endsWith('/locales/en.ts'),
);

function loadLocaleCatalog(locale: Locale): MessageCatalog {
    const localeFiles = Object.entries(localeModules).filter(([path]) =>
        path.endsWith(`/locales/${locale}.ts`),
    );
    if (localeFiles.length !== englishLocaleModules.length) {
        throw new Error(
            `Locale "${locale}" must provide a dictionary for every feature.`,
        );
    }

    const catalog: Record<string, string> = {};
    for (const [modulePath, featureMessages] of localeFiles) {
        for (const [key, value] of Object.entries(featureMessages)) {
            if (Object.hasOwn(catalog, key)) {
                throw new Error(
                    `Duplicate "${key}" translation in "${modulePath}".`,
                );
            }
            catalog[key] = value;
        }
    }

    const missingKeys = Object.keys(englishMessages).filter(
        (key) => !Object.hasOwn(catalog, key),
    );
    const unexpectedKeys = Object.keys(catalog).filter(
        (key) => !Object.hasOwn(englishMessages, key),
    );
    if (missingKeys.length > 0 || unexpectedKeys.length > 0) {
        throw new Error(
            `Locale "${locale}" has an incomplete catalog. Missing: ${missingKeys.join(', ') || 'none'}. Unexpected: ${unexpectedKeys.join(', ') || 'none'}.`,
        );
    }

    return catalog as MessageCatalog;
}

const messages = Object.fromEntries(
    supportedLocales.map(({ code }) => [code, loadLocaleCatalog(code)]),
) as Record<Locale, MessageCatalog>;

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

export const localeOptions: LocaleOption[] = supportedLocales.map(
    ({ code, name }) => ({
        locale: code,
        code: code.toUpperCase(),
        name,
    }),
);

export function parseLocale(value: string): Locale {
    const option = supportedLocales.find(({ code }) => code === value);
    if (!option) {
        throw new RangeError(`Unsupported locale: ${value}`);
    }
    return option.code;
}

export function getBrowserLocale(value: string): Locale {
    return getPreferredLocale(value, 'en');
}

export function getLocaleName(locale: Locale): string {
    return getLocaleMetadata(locale).name;
}

export function getIntlLocale(locale: Locale): string {
    return getLocaleMetadata(locale).intlTag;
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
        GOOGLE_OAUTH_FLOW_INVALID: 'error.googleOAuthFailed',
        GOOGLE_OAUTH_PROVIDER_FAILED: 'error.googleOAuthFailed',
        GOOGLE_ACCOUNT_NOT_CONNECTED: 'error.googleNotConnected',
        AI_PROVIDER_NOT_CONFIGURED: 'error.aiProviderNotConfigured',
        INVALID_REPORT_CONFIGURATION: 'error.customReportInvalid',
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
        'Google OAuth is not configured for this installation':
            'error.googleNotConfigured',
        'The Google authorization flow is invalid or expired':
            'error.googleOAuthFailed',
        'Google could not complete the authorization request':
            'error.googleOAuthFailed',
        'Google did not grant Gmail send permission':
            'error.googleOAuthFailed',
        'Google did not return a verified email address':
            'error.googleOAuthFailed',
    };
    if (keyByMessage[message]) {
        return translate(locale, keyByMessage[message]);
    }
    if (message) {
        return message;
    }
    return translate(locale, 'error.unknown');
}
