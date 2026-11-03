
import electron = require('electron');
import type {
    AiProviderKeyUpdates,
    ApiStatus,
    DesktopBridge,
} from '#/types.js';



const { contextBridge, ipcRenderer } = electron;


function subscribe<T>(
    channel: string,
    callback: (payload: T) => void,
): () => void {
    const listener = (_event: Electron.IpcRendererEvent, payload: T) =>
        callback(payload);
    ipcRenderer.on(channel, listener);
    return () => ipcRenderer.removeListener(channel, listener);
}

const desktopBridge: DesktopBridge = {
    platform: process.platform,
    bootstrap: () => ipcRenderer.invoke('app:bootstrap'),
    retryApi: () => ipcRenderer.invoke('api:retry'),
    login: (credentials) => ipcRenderer.invoke('auth:login', credentials),
    register: (credentials) => ipcRenderer.invoke('auth:register', credentials),
    logout: () => ipcRenderer.invoke('auth:logout'),
    updateProfile: (profile) => ipcRenderer.invoke('account:update', profile),
    listReports: (cursor) => ipcRenderer.invoke('reports:list', cursor),
    createReport: (request) => ipcRenderer.invoke('reports:create', request),
    getReport: (reportId) => ipcRenderer.invoke('reports:get', reportId),
    openReport: (reportId) => ipcRenderer.invoke('reports:open', reportId),
    deleteReport: (reportId) => ipcRenderer.invoke('reports:delete', reportId),
    exportReport: (reportId) =>
        ipcRenderer.invoke('reports:export', reportId),
    getPortfolio: () => ipcRenderer.invoke('portfolio:get'),
    createPortfolioTrade: (request) =>
        ipcRenderer.invoke('portfolio:trade', request),
    getGoogleStatus: () => ipcRenderer.invoke('google:status'),
    connectGoogle: () => ipcRenderer.invoke('google:connect'),
    getGoogleFlow: (flowId) => ipcRenderer.invoke('google:flow', flowId),
    disconnectGoogle: () => ipcRenderer.invoke('google:disconnect'),
    listSchedules: () => ipcRenderer.invoke('schedules:list'),
    createSchedule: (request) => ipcRenderer.invoke('schedules:create', request),
    setScheduleEnabled: (scheduleId, enabled) =>
        ipcRenderer.invoke('schedules:enabled', scheduleId, enabled),
    deleteSchedule: (scheduleId) =>
        ipcRenderer.invoke('schedules:delete', scheduleId),
    saveSettings: (settings) =>
        ipcRenderer.invoke('settings:save', settings),
    chooseFinanceScraper: () =>
        ipcRenderer.invoke('settings:choose-executable'),
    getAiProviderStatus: () =>
        ipcRenderer.invoke('integrations:ai-provider-status'),
    saveAiProviderKeys: (updates: AiProviderKeyUpdates) =>
        ipcRenderer.invoke(
            'integrations:ai-provider-keys',
            updates,
        ),
    getOllamaStatus: () => ipcRenderer.invoke('integrations:ollama-status'),
    installOllama: () => ipcRenderer.invoke('integrations:ollama-install'),
    startOllama: () => ipcRenderer.invoke('integrations:ollama-start'),
    onApiState: (callback) =>
        subscribe<ApiStatus>('desktop:api-state', callback),
    onNotification: (callback) =>
        subscribe<string>('desktop:notification', callback),
};

contextBridge.exposeInMainWorld('desktopApi', desktopBridge);
