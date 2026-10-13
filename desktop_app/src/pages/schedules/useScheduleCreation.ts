import { useState, type FormEvent } from 'react';

import type { Locale, ReportFormat } from '#/types.js';
import { formatError, translate } from '@/i18n/messages.js';

interface UseScheduleCreationOptions {
    locale: Locale;
    onRefresh: () => Promise<void>;
    onNotify: (message: string) => void;
    onError: (message: string) => void;
}

export function useScheduleCreation({
    locale,
    onRefresh,
    onNotify,
    onError,
}: UseScheduleCreationOptions) {
    const [tickers, setTickers] = useState('');
    const [runAt, setRunAt] = useState('08:00');
    const [format, setFormat] = useState<ReportFormat>('pdf');
    const [explain, setExplain] = useState(false);
    const [charts, setCharts] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const t = (key: string) => translate(locale, key);

    async function createSchedule(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        const normalizedTickers = [
            ...new Set(
                tickers
                    .split(',')
                    .map((value) => value.trim().toUpperCase())
                    .filter(Boolean),
            ),
        ];
        if (normalizedTickers.length === 0) {
            onError(
                locale === 'es'
                    ? 'Añade al menos un ticker.'
                    : 'Add at least one ticker.',
            );
            return;
        }

        setIsSaving(true);
        onError('');
        try {
            await window.desktopApi.createSchedule({
                tickers: normalizedTickers,
                report_format: format,
                run_at: runAt,
                timezone:
                    Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC',
                explain,
                mode: 'custom',
                charts,
                ml_horizon: 15,
            });
            setTickers('');
            await onRefresh();
            onNotify(t('toast.scheduleSaved'));
        } catch (scheduleError) {
            onError(formatError(locale, scheduleError));
        } finally {
            setIsSaving(false);
        }
    }

    return {
        charts,
        createSchedule,
        explain,
        format,
        isSaving,
        runAt,
        setCharts,
        setExplain,
        setFormat,
        setRunAt,
        setTickers,
        tickers,
    };
}
