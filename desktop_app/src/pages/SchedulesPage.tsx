import { useState } from 'react';
import { Check, ShieldCheck } from 'lucide-react';

import type {
    GoogleAccountStatus,
    Locale,
    ReportSchedule,
} from '#/types.js';
import { formatError, translate } from '@/i18n/messages.js';
import { GoogleConnectionCard } from '@/pages/schedules/GoogleConnectionCard.js';
import { ScheduleForm } from '@/pages/schedules/ScheduleForm.js';
import { ScheduleList } from '@/pages/schedules/ScheduleList.js';
import { useGoogleOAuthFlow } from '@/pages/schedules/useGoogleOAuthFlow.js';
import { useScheduleCreation } from '@/pages/schedules/useScheduleCreation.js';

interface SchedulesPageProps {
    locale: Locale;
    googleStatus: GoogleAccountStatus | null;
    schedules: ReportSchedule[];
    onRefresh: () => Promise<void>;
    onNotify: (message: string) => void;
}

export function SchedulesPage({
    locale,
    googleStatus,
    schedules,
    onRefresh,
    onNotify,
}: SchedulesPageProps) {
    const [error, setError] = useState<string | null>(null);
    const t = (key: string) => translate(locale, key);
    const oauth = useGoogleOAuthFlow({
        locale,
        onRefresh,
        onNotify,
        setError,
    });
    const form = useScheduleCreation({
        locale,
        onRefresh,
        onNotify,
        onError: setError,
    });

    async function setScheduleEnabled(
        schedule: ReportSchedule,
        enabled: boolean,
    ) {
        setError(null);
        try {
            await window.desktopApi.setScheduleEnabled(
                schedule.schedule_id,
                enabled,
            );
            await onRefresh();
            onNotify(t('toast.scheduleUpdated'));
        } catch (updateError) {
            setError(formatError(locale, updateError));
        }
    }

    async function deleteSchedule(schedule: ReportSchedule) {
        const confirmation =
            locale === 'es'
                ? `¿Eliminar el envío programado de ${schedule.tickers.join(', ')}?`
                : `Delete the scheduled delivery for ${schedule.tickers.join(', ')}?`;
        if (!window.confirm(confirmation)) {
            return;
        }

        setError(null);
        try {
            await window.desktopApi.deleteSchedule(schedule.schedule_id);
            await onRefresh();
        } catch (deleteError) {
            setError(formatError(locale, deleteError));
        }
    }

    return (
        <div className='page-stack'>
            <header className='page-heading'>
                <p className='eyebrow dark'>
                    <span className='signal-mark' />
                    {t('nav.schedules')}
                </p>
                <h1>{t('schedules.title')}</h1>
                <p>{t('schedules.copy')}</p>
            </header>

            <GoogleConnectionCard
                flowStatus={oauth.flowStatus}
                googleStatus={googleStatus}
                isConnecting={oauth.isConnecting}
                locale={locale}
                onConnect={() => void oauth.connectGoogle()}
                onDisconnect={() => void oauth.disconnectGoogle()}
            />

            {error && (
                <p className='form-message error-message' role='alert'>
                    {error}
                </p>
            )}

            {googleStatus?.connected && (
                <div className='schedule-layout'>
                    <ScheduleForm
                        charts={form.charts}
                        explain={form.explain}
                        format={form.format}
                        isSaving={form.isSaving}
                        locale={locale}
                        onChartsChange={form.setCharts}
                        onExplainChange={form.setExplain}
                        onFormatChange={form.setFormat}
                        onRunAtChange={form.setRunAt}
                        onSubmit={form.createSchedule}
                        onTickersChange={(value) =>
                            form.setTickers(value.toUpperCase())
                        }
                        runAt={form.runAt}
                        tickers={form.tickers}
                    />
                    <ScheduleList
                        locale={locale}
                        onDelete={(schedule) => void deleteSchedule(schedule)}
                        onToggle={(schedule, enabled) =>
                            void setScheduleEnabled(schedule, enabled)
                        }
                        schedules={schedules}
                    />
                </div>
            )}

            <section className='schedule-trust-note'>
                <ShieldCheck size={16} aria-hidden='true' />
                <div>
                    <strong>{t('schedules.keepRunning')}</strong>
                    <p>{t('schedules.systemRequirement')}</p>
                </div>
                <Check size={16} aria-hidden='true' />
            </section>
        </div>
    );
}
