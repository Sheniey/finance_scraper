
import { useEffect, useMemo, useState } from 'react';
import { FileText, Plus, Search, CalendarClock } from 'lucide-react';

import type {
    CreateReportRequest,
    Locale,
    ReportEntry,
    ReportPage,
    UserProfile,
} from '#/types.js';
import { formatError, translate } from '@/features/common/i18n/messages.js';
import { ReportTable } from '@/features/reports/components/ReportTable.js';
import { AnalysisPage } from '@/pages/AnalysisPage.js';
import PageTitle from '@/features/common/components/PageTitle.js';



interface ReportsPageProps {
    locale: Locale;
    profile: UserProfile;
    reports: ReportPage | null;
    loading: boolean;
    error: string | null;
    onCreate: (request: CreateReportRequest) => Promise<ReportEntry>;
    onOpen: (report: ReportEntry) => Promise<void>;
    onExport: (report: ReportEntry) => void;
    onDelete: (report: ReportEntry) => void;
    onExportAll: () => Promise<void>;
    onLoadMore: () => void;
    onReportsChanged: () => Promise<unknown>;
    onSaveCustomReport: (sections: string[]) => Promise<void>;
    onCreateNewSchedule: () => void;
}


const getTimeOfDay = (t: (key: string, values?: Record<string, string | number>) => string) => {
    const date = new Date();
    const hours = date.getHours();
    if (hours < 12) return t('common.goodMorning');
    if (hours < 18) return t('common.goodAfternoon');
    return t('common.goodEvening');
};


export function ReportsPage({
    locale,
    profile,
    reports,
    loading,
    error,
    onCreate,
    onOpen,
    onExport,
    onDelete,
    onExportAll,
    onLoadMore,
    onReportsChanged,
    onSaveCustomReport,
    onCreateNewSchedule,
}: ReportsPageProps) {
    const [search, setSearch] = useState('');
    const [isGenerationOpen, setIsGenerationOpen] = useState(false);
    const [refreshError, setRefreshError] = useState<string | null>(null);
    const t = (key: string, values?: Record<string, string | number>) =>
        translate(locale, key, values);

    useEffect(() => {
        let isCurrent = true;
        setRefreshError(null);
        void onReportsChanged().catch((refreshFailure: unknown) => {
            if (isCurrent) {
                setRefreshError(formatError(locale, refreshFailure));
            }
        });
        return () => {
            isCurrent = false;
        };
    }, [locale, onReportsChanged]);

    const filteredReports = useMemo(() => {
        const normalized = search.trim().toUpperCase();
        if (!normalized) {
            return reports?.items ?? [];
        }
        return (reports?.items ?? []).filter((report) =>
            `${report.ticker} ${report.filename}`
                .toUpperCase()
                .includes(normalized),
        );
    }, [reports?.items, search]);

    return (
        <div className='page-stack'>
            <header className='page-heading'>
                <PageTitle
                    sectionName={t('nav.reports')}
                    title={t('reports.greeting', {
                        timeOfDay: getTimeOfDay(t),
                        name: profile.name,
                    })}
                    copy={t('reports.copy')}
                />
                <div className='overview-quick-actions'>
                    <button
                        className='button-primary'
                        onClick={() => setIsGenerationOpen(true)}
                        type='button'
                    >
                        <Plus size={17} aria-hidden='true' />
                        {t('analysis.generate')}
                    </button>
                    <button
                        className='button-secondary'
                        onClick={() => onCreateNewSchedule()}
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
                    <label className='search-control'>
                        <Search size={16} aria-hidden='true' />
                        <span className='sr-only'>{t('reports.search')}</span>
                        <input
                            onChange={(event) => setSearch(event.target.value)}
                            placeholder={t('reports.search')}
                            type='search'
                            value={search}
                        />
                    </label>
                    <div className='dashboard-summary'>
                        <span className='dashboard-count'>
                            <FileText size={16} aria-hidden='true' />
                            <strong>{reports?.pagination.total ?? 0}</strong>
                            {t('reports.saved')}
                        </span>
                        <span className='dashboard-count'>
                            <CalendarClock size={16} aria-hidden='true' />
                            <strong>{reports?.pagination.total ?? 0}</strong>
                            {t('reports.schedules')}
                        </span>
                        <button
                            className='quiet-link'
                            onClick={() => void onExportAll()}
                            type='button'
                        >
                            {t('reports.exportAll')}
                        </button>
                    </div>
                </div>
                {(error || refreshError) && (
                    <p className='form-message error-message' role='alert'>
                        {error ?? refreshError}
                    </p>
                )}
                {filteredReports.length > 0 ? (
                    <>
                        <ReportTable
                            locale={locale}
                            onDelete={onDelete}
                            onExport={onExport}
                            onOpen={onOpen}
                            reports={filteredReports}
                        />
                        {reports?.pagination.has_more && !search && (
                            <div className='table-footer'>
                                <button
                                    className='button-secondary'
                                    disabled={loading}
                                    onClick={onLoadMore}
                                    type='button'
                                >
                                    {t('reports.loadMore')}
                                </button>
                            </div>
                        )}
                    </>
                ) : (
                    <div className='empty-state'>
                        <span className='empty-mark'>
                            <FileText size={19} aria-hidden='true' />
                        </span>
                        <strong>
                            {search
                                ? t('reports.noMatch')
                                : t('reports.empty')}
                        </strong>
                        {!search && (
                            <>
                                <p>{t('reports.emptyCopy')}</p>
                                <button
                                    className='button-secondary'
                                    onClick={() => setIsGenerationOpen(true)}
                                    type='button'
                                >
                                    <Plus size={16} aria-hidden='true' />
                                    {t('analysis.generate')}
                                </button>
                            </>
                        )}
                    </div>
                )}
            </section>

            <AnalysisPage
                isOpen={isGenerationOpen}
                locale={locale}
                onClose={() => setIsGenerationOpen(false)}
                onCreate={onCreate}
                onOpen={onOpen}
                onReportsChanged={onReportsChanged}
                onSaveCustomReport={onSaveCustomReport}
                profile={profile}
            />
        </div>
    );
}
