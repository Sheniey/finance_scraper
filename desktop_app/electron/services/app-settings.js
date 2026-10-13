import { app } from 'electron';
import { access, mkdir, readFile, rename, writeFile } from 'node:fs/promises';
import path from 'node:path';

const MIN_RETENTION_SECONDS = 10 * 60;
const MAX_RETENTION_SECONDS = 30 * 24 * 60 * 60;
const MAX_WORKER_CONCURRENCY = 16;

function defaultLocale() {
    return app.getLocale().toLowerCase().startsWith('en') ? 'en' : 'es';
}

function defaultSettings() {
    return {
        locale: defaultLocale(),
        reportRetentionSeconds: 15 * 24 * 60 * 60,
        workerMaxConcurrency: 4,
        googleClientId: process.env.GOOGLE_OAUTH_CLIENT_ID?.trim() ?? '',
        financeScraperExecutable: '',
        registeredScheduleIds: [],
    };
}

function validateSettings(value) {
    if (!value || typeof value !== 'object') {
        throw new Error('Desktop settings must be a JSON object.');
    }
    const settings = { ...defaultSettings(), ...value };
    if (!['en', 'es'].includes(settings.locale)) {
        throw new Error('Desktop language must be en or es.');
    }
    if (
        !Number.isInteger(settings.reportRetentionSeconds) ||
        settings.reportRetentionSeconds < MIN_RETENTION_SECONDS ||
        settings.reportRetentionSeconds > MAX_RETENTION_SECONDS
    ) {
        throw new Error('Report retention must be between 10 minutes and 30 days.');
    }
    if (
        !Number.isInteger(settings.workerMaxConcurrency) ||
        settings.workerMaxConcurrency < 1 ||
        settings.workerMaxConcurrency > MAX_WORKER_CONCURRENCY
    ) {
        throw new Error('Worker concurrency must be between 1 and 16.');
    }
    if (
        typeof settings.googleClientId !== 'string' ||
        typeof settings.financeScraperExecutable !== 'string' ||
        !Array.isArray(settings.registeredScheduleIds) ||
        !settings.registeredScheduleIds.every((id) => typeof id === 'string')
    ) {
        throw new Error('Desktop settings contain invalid values.');
    }
    return settings;
}

export async function readAppSettings() {
    const filePath = path.join(app.getPath('userData'), 'settings.json');
    try {
        await access(filePath);
    } catch (error) {
        if (error.code !== 'ENOENT') {
            throw error;
        }
        return defaultSettings();
    }
    const contents = await readFile(filePath, 'utf8');
    return validateSettings(JSON.parse(contents));
}

export async function writeAppSettings(value) {
    const settings = validateSettings(value);
    const userData = app.getPath('userData');
    await mkdir(userData, { recursive: true });
    const filePath = path.join(userData, 'settings.json');
    const temporary = `${filePath}.${process.pid}.tmp`;
    await writeFile(
        temporary,
        `${JSON.stringify(settings, null, 2)}\n`,
        { encoding: 'utf8', mode: 0o600 },
    );
    await rename(temporary, filePath);
    return settings;
}
