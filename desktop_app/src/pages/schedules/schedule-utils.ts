import type { Locale, ReportFormat } from '#/types.js';
import { translate } from '@/i18n/messages.js';

export const scheduleFormats: ReportFormat[] = ['pdf', 'xlsx', 'json', 'yaml'];

export function formatScheduleValue(locale: Locale, format: ReportFormat) {
    return translate(locale, `email.${format}`);
}

export function formatRunStatus(locale: Locale, value: string | null) {
    if (!value) {
        return '—';
    }

    const statusKeys: Record<string, string> = {
        IN_PROGRESS: 'status.inProgress',
        SENDING: 'status.sending',
        SENT: 'schedules.sent',
        FAILED: 'status.failed',
        DELIVERY_UNKNOWN: 'schedules.deliveryUnknown',
    };
    return translate(locale, statusKeys[value] ?? 'status.failed');
}
