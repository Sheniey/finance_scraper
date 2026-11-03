
import { useEffect, useState } from 'react';
import { Check, ShieldCheck } from 'lucide-react';

import type {
    AiProviderStatus,
    GoogleAccountStatus,
    Locale,
    OllamaStatus,
    ReportSchedule,
} from '#/types.js';
import type { ToastKind } from '@/features/common/types/index.js';
import { formatError, translate } from '@/features/common/i18n/messages.js';
import { GoogleConnectionCard } from '@/features/schedules/components/GoogleConnectionCard.js';
import { ScheduleForm } from '@/features/schedules/components/ScheduleForm.js';
import { ScheduleList } from '@/features/schedules/components/ScheduleList.js';
import { useGoogleOAuthFlow } from '@/features/schedules/hooks/useGoogleOAuthFlow.js';
import { useScheduleCreation } from '@/features/schedules/hooks/useScheduleCreation.js';
import PageTitle from '@/features/common/components/PageTitle.js';
import { APP_NAME } from '@/config.js';



interface SchedulesPageProps {
    locale: Locale;
    googleStatus: GoogleAccountStatus | null;
    schedules: ReportSchedule[];
    onRefresh: () => Promise<void>;
    onNotify: (message: string, kind?: ToastKind) => void;
}


export function SchedulesPage({
    locale,
    googleStatus,
    schedules,
    onRefresh,
    onNotify,
}: SchedulesPageProps) {
    const [error, setError] = useState<string | null>(null);
    const [isCheckingAi, setIsCheckingAi] = useState(true);
    const [aiAvailable, setAiAvailable] = useState(false);
    const t = (
        key: string,
        values?: Record<string, string | number>,
    ) => translate(locale, key, values);
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

    useEffect(() => {
        let isCurrent = true;
        void Promise.all([
            window.desktopApi.getAiProviderStatus(),
            window.desktopApi.getOllamaStatus(),
        ])
            .then(
                ([providerStatus, ollamaStatus]: [
                    AiProviderStatus,
                    OllamaStatus,
                ]) => {
                    if (isCurrent) {
                        const isAvailable =
                            Object.values(providerStatus).some(Boolean) ||
                            (ollamaStatus.running &&
                                ollamaStatus.models.length > 0);
                        setAiAvailable(isAvailable);
                        if (!isAvailable) {
                            form.setExplain(false);
                        }
                    }
                },
            )
            .catch((statusError: unknown) => {
                if (isCurrent) {
                    setError(formatError(locale, statusError));
                }
            })
            .finally(() => {
                if (isCurrent) {
                    setIsCheckingAi(false);
                }
            });
        return () => {
            isCurrent = false;
        };
    }, [locale, form.setExplain]);

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
            onNotify(t('toast.scheduleUpdated'), 'success');
        } catch (updateError) {
            setError(formatError(locale, updateError));
        }
    }

    async function deleteSchedule(schedule: ReportSchedule) {
        const confirmation = t('schedules.confirmDelete', {
            tickers: schedule.tickers.join(', '),
        });
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
                <PageTitle
                    sectionName={t('nav.schedules')}
                    title={t('schedules.title')}
                    copy={t('schedules.copy')}
                />
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
                        aiAvailable={aiAvailable && !isCheckingAi}
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
                    <strong>{t('schedules.keepRunning', { app_name: APP_NAME })}</strong>
                    <p>{t('schedules.systemRequirement')}</p>
                </div>
                <Check size={16} aria-hidden='true' />
            </section>
        </div>
    );
}
