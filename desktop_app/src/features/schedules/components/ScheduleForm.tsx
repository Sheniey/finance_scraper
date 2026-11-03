
import type { FormEvent } from 'react';
import { motion } from 'motion/react';
import {
    CalendarClock,
    Clock3,
    Mail,
    Plus,
    ShieldCheck,
} from 'lucide-react';

import type { Locale, ReportFormat } from '#/types.js';
import { LoadingSpinner } from '@/features/common/components/LoadingSpinner.js';
import { translate } from '@/features/common/i18n/messages.js';
import { formatScheduleValue, scheduleFormats } from '@/features/schedules/lib/schedule-utils.js';



interface ScheduleFormProps {
    locale: Locale;
    tickers: string;
    runAt: string;
    format: ReportFormat;
    explain: boolean;
    charts: boolean;
    aiAvailable: boolean;
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
    aiAvailable,
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
            <motion.label
                animate={{
                    backgroundColor: charts ? '#f5faf8' : '#ffffff',
                    borderColor: charts
                        ? 'rgba(36, 122, 119, 0.28)'
                        : 'rgba(13, 23, 38, 0.08)',
                }}
                className='choice-row'
                initial={false}
                transition={{ duration: 0.15, ease: 'easeOut' }}
                whileTap={{ scale: 0.992 }}
            >
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
                <motion.span
                    animate={{
                        backgroundColor: charts ? '#247a77' : '#d5d9dd',
                    }}
                    className='toggle-track'
                    initial={false}
                    transition={{
                        type: 'spring',
                        stiffness: 520,
                        damping: 34,
                    }}
                    aria-hidden='true'
                >
                    <motion.span
                        animate={{ x: charts ? 15 : 0 }}
                        className='toggle-thumb'
                        initial={false}
                        transition={{
                            type: 'spring',
                            stiffness: 520,
                            damping: 34,
                        }}
                    />
                </motion.span>
            </motion.label>
            <motion.label
                animate={{
                    backgroundColor: explain ? '#f5faf8' : '#ffffff',
                    borderColor: explain
                        ? 'rgba(36, 122, 119, 0.28)'
                        : 'rgba(13, 23, 38, 0.08)',
                }}
                className='choice-row'
                initial={false}
                transition={{ duration: 0.15, ease: 'easeOut' }}
                whileTap={{ scale: 0.992 }}
            >
                <span className='choice-icon'>
                    <Mail size={17} aria-hidden='true' />
                </span>
                <span className='choice-copy'>
                    <strong>{t('analysis.explain')}</strong>
                    <small>
                        {aiAvailable
                            ? t('analysis.explainCopy')
                            : t('analysis.aiUnavailable')}
                    </small>
                </span>
                <input
                    checked={explain}
                    disabled={!aiAvailable}
                    onChange={(event) => onExplainChange(event.target.checked)}
                    type='checkbox'
                />
                <motion.span
                    animate={{
                        backgroundColor: explain ? '#247a77' : '#d5d9dd',
                    }}
                    className='toggle-track'
                    initial={false}
                    transition={{
                        type: 'spring',
                        stiffness: 520,
                        damping: 34,
                    }}
                    aria-hidden='true'
                >
                    <motion.span
                        animate={{ x: explain ? 15 : 0 }}
                        className='toggle-thumb'
                        initial={false}
                        transition={{
                            type: 'spring',
                            stiffness: 520,
                            damping: 34,
                        }}
                    />
                </motion.span>
            </motion.label>
            <button
                className='button-primary form-primary'
                disabled={isSaving}
                type='submit'
            >
                {isSaving ? (
                    <LoadingSpinner size={16} />
                ) : (
                    <Plus size={16} aria-hidden='true' />
                )}
                {isSaving ? t('common.saving') : t('schedules.createAction')}
            </button>
        </form>
    );
}
