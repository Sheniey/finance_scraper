import type { DesktopBridge } from '#/types.js';

const requiredMethods = [
    'bootstrap',
    'retryApi',
    'login',
    'loginWithGoogle',
    'register',
    'logout',
    'updateProfile',
    'listReports',
    'createReport',
    'getReport',
    'openReport',
    'deleteReport',
    'getGoogleStatus',
    'connectGoogle',
    'getGoogleFlow',
    'disconnectGoogle',
    'listSchedules',
    'createSchedule',
    'setScheduleEnabled',
    'deleteSchedule',
    'saveSettings',
    'chooseFinanceScraper',
    'getAiProviderStatus',
    'saveAiProviderKeys',
    'onApiState',
    'onNotification',
] satisfies Array<keyof DesktopBridge>;

export function hasCompleteDesktopBridge(
    candidate: unknown,
): candidate is DesktopBridge {
    if (typeof candidate !== 'object' || candidate === null) {
        return false;
    }
    if (typeof Reflect.get(candidate, 'platform') !== 'string') {
        return false;
    }
    return requiredMethods.every(
        (method) => typeof Reflect.get(candidate, method) === 'function',
    );
}
