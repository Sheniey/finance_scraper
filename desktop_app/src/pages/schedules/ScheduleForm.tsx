import type { FormEvent } from 'react';
import {
    CalendarClock,
    Clock3,
    Mail,
    Plus,
    ShieldCheck,
} from 'lucide-react';

import type { Locale, ReportFormat } from '#/types.js';
import { translate } from '@/i18n/messages.js';
import { formatScheduleValue, scheduleFormats } from './schedule-utils.js';

interface ScheduleFormProps {
    locale: Locale;
    tickers: string;
    runAt: string;
    format: ReportFormat;
    explain: boolean;
    charts: boolean;
    isSaving: boolean;
    onTickersChange: (value: string) => void;
    onRunAtChange: (value: string) => void;
    onFormatChange: (value: ReportFormat) => void;
    onExplainChange: (value: boolean) => void;
    onChartsChange: (value: boolean) => void;
    onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}

export function ScheduleForm({
    locale,
    tickers,
    runAt,
    format,
    explain,
    charts,
    isSaving,
    onTickersChange,
    onRunAtChange,
    onFormatChange,
    onExplainChange,
    onChartsChange,
    onSubmit,
}: ScheduleFormProps) {
    const t = (key: string) => translate(locale, key);
    const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';

    return (
        <form className='content-panel schedule-form' onSubmit={onSubmit}>
            <div className='panel-heading-row'>
                <div>
                    <p className='field-kicker'>{t('schedules.add')}</p>
                    <h2>{t('schedules.createAction')}</h2>
                </div>
                <span className='panel-symbol'>
                    <CalendarClock size={18} aria-hidden='true' />
                </span>
            </div>
            <label className='form-field'>
                <span>{t('schedules.tickers')}</span>
                <input
                    autoCapitalize='characters'
                    onChange={(event) => onTickersChange(event.target.value)}
                    placeholder='AAPL, NVDA'
                    value={tickers}
                />
            </label>
            <div className='form-grid two-column'>
                <label className='form-field'>
                    <span>{t('schedules.time')}</span>
                    <span className='field-with-icon'>
                        <Clock3 size={16} aria-hidden='true' />
                        <input
                            onChange={(event) => onRunAtChange(event.target.value)}
                            required
                            type='time'
                            value={runAt}
                        />
                    </span>
                </label>
                <label className='form-field'>
                    <span>{t('schedules.format')}</span>
                    <select
                        onChange={(event) =>
                            onFormatChange(event.target.value as ReportFormat)
                        }
                        value={format}
                    >
                        {scheduleFormats.map((item) => (
                            <option key={item} value={item}>
                                {formatScheduleValue(locale, item)}
                            </option>
                        ))}
                    </select>
                </label>
            </div>
            <p className='timezone-note'>
                {t('schedules.timezone')}: <code>{timeZone}</code>
            </p>
            <label className='choice-row'>
                <span className='choice-icon'>
                    <ShieldCheck size={17} aria-hidden='true' />
                </span>
                <span className='choice-copy'>
                    <strong>{t('analysis.charts')}</strong>
                </span>
                <input
                    checked={charts}
                    onChange={(event) => onChartsChange(event.target.checked)}
                    type='checkbox'
                />
                <span className='toggle-track' aria-hidden='true' />
            </label>
            <label className='choice-row'>
                <span className='choice-icon'>
                    <Mail size={17} aria-hidden='true' />
                </span>
                <span className='choice-copy'>
                    <strong>{t('analysis.explain')}</strong>
                </span>
                <input
                    checked={explain}
                    onChange={(event) => onExplainChange(event.target.checked)}
                    type='checkbox'
                />
                <span className='toggle-track' aria-hidden='true' />
            </label>
            <button
                className='button-primary form-primary'
                disabled={isSaving}
                type='submit'
            >
                <Plus size={16} aria-hidden='true' />
                {isSaving ? t('common.saving') : t('schedules.createAction')}
            </button>
        </form>
    );
}
