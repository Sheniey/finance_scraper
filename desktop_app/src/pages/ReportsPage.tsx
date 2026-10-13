import { useMemo, useState } from 'react';
import { Search, Trash2 } from 'lucide-react';

import type { Locale, ReportEntry, ReportPage } from '#/types.js';
import { translate } from '@/i18n/messages.js';
import { ReportTable } from '@/components/ReportTable.js';

interface ReportsPageProps {
    locale: Locale;
    reports: ReportPage | null;
    loading: boolean;
    error: string | null;
    onOpen: (report: ReportEntry) => void;
    onDelete: (report: ReportEntry) => void;
    onLoadMore: () => void;
}

export function ReportsPage({
    locale,
    reports,
    loading,
    error,
    onOpen,
    onDelete,
    onLoadMore,
}: ReportsPageProps) {
    const [search, setSearch] = useState('');
    const t = (key: string, values?: Record<string, string | number>) =>
        translate(locale, key, values);
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
            <header className='page-heading split-heading'>
                <div>
                    <p className='eyebrow dark'>
                        <span className='signal-mark' />
                        {t('nav.reports')}
                    </p>
                    <h1>{t('reports.title')}</h1>
                    <p>{t('reports.copy')}</p>
                </div>
                <span className='report-total'>
                    <strong>{reports?.pagination.total ?? 0}</strong>
                    <small>{t('overview.reports')}</small>
                </span>
            </header>

            <section className='content-panel'>
                <div className='report-toolbar'>
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
                    {loading && (
                        <span className='subtle-loading'>{t('common.loading')}</span>
                    )}
                </div>
                {error && (
                    <p className='form-message error-message' role='alert'>
                        {error}
                    </p>
                )}
                {filteredReports.length > 0 ? (
                    <>
                        <ReportTable
                            locale={locale}
                            onDelete={onDelete}
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
                            <Trash2 size={19} aria-hidden='true' />
                        </span>
                        <strong>
                            {search
                                ? t('reports.noMatch')
                                : t('overview.noReports')}
                        </strong>
                        {!search && <p>{t('overview.firstReport')}</p>}
                    </div>
                )}
            </section>
        </div>
    );
}
