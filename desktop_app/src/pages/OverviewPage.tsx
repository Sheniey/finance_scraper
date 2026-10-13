import { CalendarClock, FileText, Plus } from 'lucide-react';

import type {
    GoogleAccountStatus,
    Locale,
    ReportEntry,
    ReportPage,
    ReportSchedule,
    UserProfile,
} from '#/types.js';
import { ReportTable } from '@/components/ReportTable.js';
import { translate } from '@/i18n/messages.js';

interface OverviewPageProps {
    locale: Locale;
    profile: UserProfile;
    reports: ReportPage | null;
    schedules: ReportSchedule[];
    googleStatus: GoogleAccountStatus | null;
    loading: boolean;
    onNavigate: (view: 'analysis' | 'reports' | 'schedules') => void;
    onOpenReport: (report: ReportEntry) => void;
    onDeleteReport: (report: ReportEntry) => void;
}

export function OverviewPage({
    locale,
    profile,
    reports,
    schedules,
    googleStatus,
    loading,
    onNavigate,
    onOpenReport,
    onDeleteReport,
}: OverviewPageProps) {
    const t = (key: string, values?: Record<string, string | number>) =>
        translate(locale, key, values);
    const recentReports = reports?.items.slice(0, 5) ?? [];
    const greetingName = profile.name.split(/\s+/)[0] || profile.name;
    const scheduleCount = schedules.filter((schedule) => schedule.enabled).length;
    const reportCount = reports?.pagination.total ?? 0;

    return (
        <div className='page-stack'>
            <header className='overview-heading'>
                <div>
                    <p className='eyebrow dark'>
                        <span className='signal-mark' />
                        {t('overview.kicker')}
                    </p>
                    <h1>{t('overview.greeting', { name: greetingName })}</h1>
                    <p>{t('overview.copy')}</p>
                </div>
                <div className='overview-quick-actions'>
                    <button
                        className='button-primary'
                        onClick={() => onNavigate('analysis')}
                        type='button'
                    >
                        <Plus size={18} aria-hidden='true' />
                        {t('analysis.generate')}
                    </button>
                    <button
                        className='button-secondary'
                        onClick={() => onNavigate('schedules')}
                        type='button'
                    >
                        <CalendarClock size={17} aria-hidden='true' />
                        {t('schedules.add')}
                    </button>
                </div>
            </header>

            <section
                aria-labelledby='dashboard-reports-title'
                className='content-panel dashboard-library-panel'
            >
                <div className='panel-heading-row dashboard-library-heading'>
                    <div>
                        <p className='field-kicker'>{t('overview.recent')}</p>
                        <h2 id='dashboard-reports-title'>
                            {t('reports.title')}
                        </h2>
                    </div>
                    <div className='dashboard-summary'>
                        <span className='dashboard-count'>
                            <FileText size={16} aria-hidden='true' />
                            <strong>{reportCount}</strong>
                            {t('overview.reports')}
                        </span>
                        <span className='dashboard-count'>
                            <CalendarClock size={16} aria-hidden='true' />
                            <strong>{scheduleCount}</strong>
                            {t('overview.schedules')}
                        </span>
                        <button
                            className='quiet-link'
                            onClick={() => onNavigate('reports')}
                            type='button'
                        >
                            {t('overview.allReports')}
                        </button>
                    </div>
                </div>

                {loading && (
                    <p className='dashboard-loading' role='status'>
                        {t('common.loading')}
                    </p>
                )}
                {recentReports.length > 0 ? (
                    <ReportTable
                        locale={locale}
                        onDelete={onDeleteReport}
                        onOpen={onOpenReport}
                        reports={recentReports}
                    />
                ) : (
                    <div className='empty-state dashboard-empty-state'>
                        <span className='empty-mark'>
                            <FileText size={20} aria-hidden='true' />
                        </span>
                        <strong>{t('overview.noReports')}</strong>
                        <p>{t('overview.firstReport')}</p>
                        <button
                            className='button-secondary'
                            onClick={() => onNavigate('analysis')}
                            type='button'
                        >
                            <Plus size={16} aria-hidden='true' />
                            {t('overview.create')}
                        </button>
                    </div>
                )}

                {googleStatus?.connected && (
                    <p className='integration-note'>
                        <span className='health-dot online' aria-hidden='true' />
                        {t('overview.googleConnected')}
                    </p>
                )}
            </section>
        </div>
    );
}
