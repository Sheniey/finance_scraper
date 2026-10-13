import {
    app,
    BrowserWindow,
    dialog,
    ipcMain,
    shell,
} from 'electron';
import path from 'node:path';

import { FinanceApiClient } from './services/api-client.js';
import {
    readAppSettings,
    writeAppSettings,
} from './services/app-settings.js';
import { LocalApiManager } from './services/local-api.js';
import { WindowsTaskScheduler } from './services/task-scheduler.js';
import { getInstallationSecrets } from './services/secure-vault.js';

app.setName('Finance Scraper');
const isolatedUserDataPath =
    !app.isPackaged && process.env.FINANCE_DESKTOP_USER_DATA;
const financeScraperUserData = isolatedUserDataPath
    ? path.resolve(isolatedUserDataPath)
    : path.join(app.getPath('appData'), 'Finance Scraper');
app.setPath('userData', financeScraperUserData);
app.setPath('sessionData', path.join(financeScraperUserData, 'Session Data'));

const SINGLE_INSTANCE_LOCK = app.requestSingleInstanceLock();
const BACKGROUND_SCHEDULE_PREFIX = '--scheduled-task=';
const TRUSTED_DEV_ORIGINS = new Set([
    'http://127.0.0.1:5173',
    'http://localhost:5173',
]);

let mainWindow = null;
let appSettings = {
    locale: 'es',
    reportRetentionSeconds: 15 * 24 * 60 * 60,
    workerMaxConcurrency: 4,
    googleClientId: '',
    financeScraperExecutable: '',
    registeredScheduleIds: [],
};
let installationSecrets = null;
let apiManager = null;
let apiClient = null;
let taskScheduler = null;
let bootstrapError = null;
let isShuttingDown = false;
let shutdownComplete = false;
let ipcHandlersRegistered = false;
const activeScheduledRuns = new Set();
const pendingSecondInstanceArguments = [];

function publicSettings(settings) {
    return {
        locale: settings.locale,
        reportRetentionSeconds: settings.reportRetentionSeconds,
        workerMaxConcurrency: settings.workerMaxConcurrency,
        googleClientId: settings.googleClientId,
        financeScraperExecutable: settings.financeScraperExecutable,
    };
}

function sendApiStatus(status) {
    for (const window of BrowserWindow.getAllWindows()) {
        window.webContents.send('desktop:api-state', status);
    }
}

function assertTrustedRenderer(event) {
    const senderUrl = event.senderFrame?.url ?? event.sender.getURL();
    if (app.isPackaged) {
        if (!senderUrl.startsWith('file://')) {
            throw new Error('Untrusted renderer origin.');
        }
        return;
    }
    if (!TRUSTED_DEV_ORIGINS.has(new URL(senderUrl).origin)) {
        throw new Error('Untrusted renderer origin.');
    }
}

function registerHandler(channel, handler) {
    ipcMain.handle(channel, (event, ...args) => {
        assertTrustedRenderer(event);
        return handler(...args);
    });
}

async function requestInternal(endpoint, options = {}) {
    const response = await apiManager.request(endpoint, {
        ...options,
        internal: true,
    });
    const content = await response.text();
    let payload = null;
    if (content) {
        try {
            payload = JSON.parse(content);
        } catch (error) {
            throw new Error(
                `The local API returned invalid JSON (HTTP ${response.status}).`,
                { cause: error },
            );
        }
    }
    if (!response.ok) {
        throw new Error(
            payload?.message ||
                `The local API request failed (HTTP ${response.status}).`,
        );
    }
    return payload;
}

async function reconcileScheduledTasks() {
    if (!apiManager || !taskScheduler) {
        throw new Error('Desktop scheduling services are not initialized.');
    }
    const registry = await requestInternal('/schedules/desktop/registry');
    const registeredScheduleIds = await taskScheduler.reconcile(
        registry.schedules,
        appSettings.registeredScheduleIds,
    );
    appSettings = await writeAppSettings({
        ...appSettings,
        registeredScheduleIds,
    });
}

async function runScheduledInvocation(scheduleId = null) {
    const operation = (async () => {
        await apiManager.start();
        const result = scheduleId
            ? await requestInternal(
                `/schedules/desktop/${encodeURIComponent(scheduleId)}/run`,
                { method: 'POST' },
            )
            : await requestInternal('/schedules/desktop/run-due', {
                method: 'POST',
            });
        await reconcileScheduledTasks();
        return result;
    })();
    activeScheduledRuns.add(operation);
    try {
        return await operation;
    } finally {
        activeScheduledRuns.delete(operation);
    }
}

function parseBackgroundCommand(argumentsList) {
    const scheduledArgument = argumentsList.find((argument) =>
        argument.startsWith(BACKGROUND_SCHEDULE_PREFIX),
    );
    if (scheduledArgument) {
        return {
            type: 'schedule',
            scheduleId: scheduledArgument.slice(
                BACKGROUND_SCHEDULE_PREFIX.length,
            ),
        };
    }
    if (argumentsList.includes('--recover-schedules')) {
        return { type: 'recovery', scheduleId: null };
    }
    return null;
}

async function runBackgroundCommand(
    command,
    { quitAfter = false } = {},
) {
    let failure = null;
    try {
        const result = await runScheduledInvocation(command.scheduleId);
        console.info(
            'Scheduled report helper completed:',
            command.scheduleId ?? 'recovery',
            result?.status ?? 'checked',
        );
    } catch (error) {
        console.error('Scheduled report helper failed:', error.message);
        failure = error;
        if (mainWindow) {
            mainWindow.webContents.send(
                'desktop:notification',
                'SCHEDULE_RECOVERY_FAILED',
            );
        }
    }

    if (quitAfter) {
        try {
            const stopResult = await apiManager?.stop();
            if (stopResult?.warning) {
                console.warn('Local API shutdown warning:', stopResult.warning);
            }
        } catch (stopError) {
            failure ??= stopError;
            console.error('Could not stop the local API:', stopError.message);
        }
        shutdownComplete = true;
        if (failure) {
            app.exit(1);
        } else {
            app.quit();
        }
    }
}

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1440,
        height: 920,
        minWidth: 960,
        minHeight: 680,
        backgroundColor: '#0d1726',
        autoHideMenuBar: true,
        webPreferences: {
            contextIsolation: true,
            nodeIntegration: false,
            sandbox: true,
            preload: path.join(
                app.getAppPath(),
                'dist',
                'preload',
                'index.cjs',
            ),
        },
    });

    mainWindow.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
    mainWindow.webContents.on('will-navigate', (event, url) => {
        const trusted = app.isPackaged
            ? url.startsWith('file://')
            : TRUSTED_DEV_ORIGINS.has(new URL(url).origin);
        if (!trusted) {
            event.preventDefault();
        }
    });
    mainWindow.on('closed', () => {
        mainWindow = null;
    });

    if (app.isPackaged) {
        mainWindow.loadFile(path.join(app.getAppPath(), 'dist', 'index.html'));
    } else {
        mainWindow.loadURL('http://127.0.0.1:5173');
    }
}

function getProfileId() {
    const profileId = apiClient?.getProfile()?.id;
    if (!profileId) {
        throw new Error('Sign in before opening a report.');
    }
    return profileId;
}

async function openReport(reportId) {
    const report = await requireApiClient().getReport(reportId);
    if (report.status !== 'COMPLETED' || !report.download_url) {
        throw new Error('This report is not ready to open yet.');
    }
    const extension = report.report_format.toLowerCase();
    if (!['pdf', 'json', 'yaml', 'txt', 'xlsx'].includes(extension)) {
        throw new Error('The report format is not supported by the desktop app.');
    }
    const profileId = getProfileId();
    if (!/^[0-9a-f-]{36}$/i.test(profileId)) {
        throw new Error('The signed-in profile ID has an invalid format.');
    }
    const safeFilename = path
        .basename(report.filename)
        .replace(/[^A-Za-z0-9._ -]/g, '_');
    if (
        !safeFilename ||
        path.extname(safeFilename).toLowerCase() !== `.${extension}`
    ) {
        throw new Error('The report filename is invalid.');
    }
    const { content } = await requireApiClient().downloadReport(reportId);
    const profileDirectory = path.join(
        app.getPath('temp'),
        'Finance Scraper',
        profileId,
    );
    const filename = `${reportId}-${safeFilename}`;
    const outputPath = path.join(profileDirectory, filename);
    const resolvedDirectory = path.resolve(profileDirectory);
    if (!path.resolve(outputPath).startsWith(`${resolvedDirectory}${path.sep}`)) {
        throw new Error('The report download path is invalid.');
    }
    const { mkdir, writeFile } = await import('node:fs/promises');
    await mkdir(profileDirectory, { recursive: true });
    await writeFile(outputPath, content, { mode: 0o600 });
    const openError = await shell.openPath(outputPath);
    if (openError) {
        throw new Error(openError);
    }
    return { path: outputPath };
}

async function saveSettings(patch) {
    const allowedKeys = new Set([
        'locale',
        'reportRetentionSeconds',
        'workerMaxConcurrency',
        'googleClientId',
        'financeScraperExecutable',
    ]);
    for (const key of Object.keys(patch)) {
        if (!allowedKeys.has(key)) {
            throw new Error(`Unsupported desktop setting: ${key}`);
        }
    }
    const previousSettings = appSettings;
    const nextSettings = await writeAppSettings({
        ...appSettings,
        ...patch,
    });
    const restartRequired = [
        'reportRetentionSeconds',
        'workerMaxConcurrency',
        'googleClientId',
        'financeScraperExecutable',
    ].some((key) => nextSettings[key] !== previousSettings[key]);
    appSettings = nextSettings;

    if (!apiManager) {
        await initializeRuntime();
        return getBootstrap();
    }
    if (restartRequired && apiManager.getStatus().state === 'online') {
        try {
            const stopResult = await apiManager.stop();
            if (stopResult.warning) {
                console.warn('Local API restart warning:', stopResult.warning);
            }
            await apiManager.start();
            await reconcileScheduledTasks();
        } catch (error) {
            appSettings = await writeAppSettings(previousSettings);
            try {
                await apiManager.start();
            } catch (restartError) {
                throw new AggregateError(
                    [error, restartError],
                    'Settings could not be applied and the previous API configuration could not be restored.',
                );
            }
            throw error;
        }
    }
    return getBootstrap();
}

function getBootstrap() {
    return {
        api: apiManager?.getStatus() ?? {
            state: 'stopped',
            baseUrl: null,
            workerConcurrency: null,
        },
        settings: publicSettings(appSettings),
        profile: apiClient?.getProfile() ?? null,
        workerConcurrency: apiManager?.getStatus().workerConcurrency ?? null,
        error: bootstrapError,
    };
}

function requireApiClient() {
    if (!apiClient) {
        throw new Error(
            bootstrapError || 'Finance Scraper API is not available.',
        );
    }
    return apiClient;
}

function registerIpcHandlers() {
    if (ipcHandlersRegistered) {
        return;
    }
    ipcHandlersRegistered = true;
    registerHandler('app:bootstrap', async () => getBootstrap());
    registerHandler('api:retry', async () => {
        bootstrapError = null;
        if (!apiManager) {
            await initializeRuntime();
            return apiManager.getStatus();
        }
        const status = await apiManager.start();
        await reconcileScheduledTasks();
        return status;
    });
    registerHandler('auth:login', async (credentials) => {
        const profile = await requireApiClient().login(credentials);
        return profile;
    });
    registerHandler('auth:google-login', async () => {
        const client = requireApiClient();
        const flow = await client.startGoogleLogin();
        await shell.openExternal(flow.authorization_url);
        return client.waitForGoogleLogin(flow.flow_id);
    });
    registerHandler('auth:register', async (credentials) =>
        requireApiClient().register(credentials),
    );
    registerHandler('auth:logout', async () =>
        requireApiClient().logout(),
    );
    registerHandler('account:update', async (profile) =>
        requireApiClient().updateProfile(profile),
    );
    registerHandler('reports:list', async (cursor) =>
        requireApiClient().listReports(cursor),
    );
    registerHandler('reports:create', async (request) =>
        requireApiClient().createReport(request),
    );
    registerHandler('reports:get', async (reportId) =>
        requireApiClient().getReport(reportId),
    );
    registerHandler('reports:open', async (reportId) =>
        openReport(reportId),
    );
    registerHandler('reports:delete', async (reportId) =>
        requireApiClient().deleteReport(reportId),
    );
    registerHandler('google:status', async () =>
        requireApiClient().getGoogleStatus(),
    );
    registerHandler('google:connect', async () => {
        const flow = await requireApiClient().connectGoogle();
        await shell.openExternal(flow.authorization_url);
        return { flow_id: flow.flow_id };
    });
    registerHandler('google:flow', async (flowId) =>
        requireApiClient().getGoogleFlow(flowId),
    );
    registerHandler('google:disconnect', async () => {
        const result = await requireApiClient().disconnectGoogle();
        await reconcileScheduledTasks();
        return {
            ...result,
            ...(await requireApiClient().getGoogleStatus()),
        };
    });
    registerHandler('schedules:list', async () => {
        const result = await requireApiClient().listSchedules();
        return result.schedules;
    });
    registerHandler('schedules:create', async (request) => {
        const schedule = await requireApiClient().createSchedule(request);
        try {
            await reconcileScheduledTasks();
        } catch (error) {
            try {
                await requireApiClient().deleteSchedule(schedule.schedule_id);
                await reconcileScheduledTasks();
            } catch (rollbackError) {
                throw new AggregateError(
                    [error, rollbackError],
                    'The schedule could not be registered or rolled back.',
                );
            }
            throw error;
        }
        return schedule;
    });
    registerHandler(
        'schedules:enabled',
        async (scheduleId, enabled) => {
            const schedule = await requireApiClient().setScheduleEnabled(
                scheduleId,
                enabled,
            );
            try {
                await reconcileScheduledTasks();
            } catch (error) {
                try {
                    await requireApiClient().setScheduleEnabled(
                        scheduleId,
                        !enabled,
                    );
                    await reconcileScheduledTasks();
                } catch (rollbackError) {
                    throw new AggregateError(
                        [error, rollbackError],
                        'The schedule could not be updated or rolled back.',
                    );
                }
                throw error;
            }
            return schedule;
        },
    );
    registerHandler('schedules:delete', async (scheduleId) => {
        await requireApiClient().deleteSchedule(scheduleId);
        await reconcileScheduledTasks();
    });
    registerHandler('settings:save', async (patch) =>
        saveSettings(patch),
    );
    registerHandler('integrations:ai-provider-status', async () => {
        if (!apiManager) {
            throw new Error('The local application is not ready.');
        }
        return apiManager.getAiProviderStatus();
    });
    registerHandler('integrations:ai-provider-keys', async (updates) => {
        if (!apiManager) {
            throw new Error('The local application is not ready.');
        }
        return apiManager.saveAiProviderKeys(updates);
    });
    registerHandler('settings:choose-executable', async () => {
        const options = {
            title: 'Choose finance-scraper.exe',
            properties: ['openFile'],
            filters: [{ name: 'Finance Scraper', extensions: ['exe'] }],
        };
        const result = mainWindow
            ? await dialog.showOpenDialog(mainWindow, options)
            : await dialog.showOpenDialog(options);
        const selectedPath = result.filePaths[0];
        if (result.canceled || !selectedPath) {
            return null;
        }
        if (path.basename(selectedPath).toLowerCase() !== 'finance-scraper.exe') {
            throw new Error('Choose the finance-scraper.exe application.');
        }
        return selectedPath;
    });
}

async function initializeRuntime() {
    installationSecrets ??= await getInstallationSecrets();
    appSettings = await readAppSettings();
    if (!apiManager) {
        apiManager = new LocalApiManager({
            appInstance: app,
            getSettings: async () => appSettings,
            getSecrets: async () => installationSecrets,
            onState: sendApiStatus,
        });
        apiClient = new FinanceApiClient(apiManager);
        taskScheduler = new WindowsTaskScheduler(app);
    }
    await apiManager.start();
    await reconcileScheduledTasks();
    bootstrapError = null;
}

async function initializeApplication() {
    const backgroundCommand = parseBackgroundCommand(process.argv);
    registerIpcHandlers();
    try {
        await initializeRuntime();
    } catch (error) {
        bootstrapError = error.message;
        console.error('Finance Scraper API could not start:', error.message);
    }

    try {
        if (backgroundCommand) {
            if (!apiManager || apiManager.getStatus().state !== 'online') {
                await initializeRuntime();
            }
            await runBackgroundCommand(backgroundCommand, {
                quitAfter: true,
            });
            return;
        }

        createWindow();
        if (apiManager?.getStatus().state === 'online') {
            void runScheduledInvocation().catch((error) => {
                console.error('Scheduled report recovery failed:', error.message);
                for (const window of BrowserWindow.getAllWindows()) {
                    window.webContents.send(
                        'desktop:notification',
                        'SCHEDULE_RECOVERY_FAILED',
                    );
                }
            });
        }

        for (const args of pendingSecondInstanceArguments.splice(0)) {
            handleSecondInstanceArguments(args);
        }
    } catch (error) {
        bootstrapError = error.message;
        console.error('Finance Scraper desktop initialization failed:', error.message);
        if (backgroundCommand) {
            app.exit(1);
            return;
        }
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        }
    }
}

function handleSecondInstanceArguments(argumentsList) {
    const backgroundCommand = parseBackgroundCommand(argumentsList);
    if (backgroundCommand) {
        void runBackgroundCommand(backgroundCommand, {
            quitAfter: false,
        });
        return;
    }
    if (mainWindow) {
        if (mainWindow.isMinimized()) {
            mainWindow.restore();
        }
        mainWindow.focus();
    }
}

async function shutdownApplication() {
    await Promise.allSettled([...activeScheduledRuns]);
    if (apiClient?.getProfile()) {
        try {
            await apiClient.logout();
        } catch (error) {
            console.error('Could not revoke the UI session on close:', error.message);
        }
    }
    if (apiManager) {
        const result = await apiManager.stop();
        if (result.warning) {
            console.error('API shutdown required a forced stop:', result.warning);
        }
    }
}

if (!SINGLE_INSTANCE_LOCK) {
    app.quit();
} else {
    app.on('second-instance', (_event, argumentsList) => {
        if (!apiManager) {
            pendingSecondInstanceArguments.push(argumentsList);
            return;
        }
        handleSecondInstanceArguments(argumentsList);
    });

    app.whenReady().then(initializeApplication);

    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0 && !isShuttingDown) {
            createWindow();
        }
    });

    app.on('before-quit', (event) => {
        if (shutdownComplete) {
            return;
        }
        event.preventDefault();
        if (isShuttingDown) {
            return;
        }
        isShuttingDown = true;
        shutdownApplication()
            .catch((error) => {
                console.error('Finance Scraper shutdown failed:', error.message);
            })
            .finally(() => {
                shutdownComplete = true;
                app.quit();
            });
    });

    app.on('window-all-closed', () => {
        app.quit();
    });
}
