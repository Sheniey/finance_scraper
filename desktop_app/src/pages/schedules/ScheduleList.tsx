import {
    CalendarClock,
    Pause,
    Play,
    Trash2,
} from 'lucide-react';

import type { Locale, ReportSchedule } from '#/types.js';
import { translate } from '@/i18n/messages.js';
import { formatRunStatus, formatScheduleValue } from './schedule-utils.js';

interface ScheduleListProps {
    locale: Locale;
    schedules: ReportSchedule[];
    onToggle: (schedule: ReportSchedule, enabled: boolean) => void;
    onDelete: (schedule: ReportSchedule) => void;
}

export function ScheduleList({
    locale,
    schedules,
    onToggle,
    onDelete,
}: ScheduleListProps) {
    const t = (key: string, values?: Record<string, string | number>) =>
        translate(locale, key, values);

    return (
        <div className='schedule-list-column'>
            <section className='content-panel schedule-list-panel'>
                <div className='panel-heading-row'>
                    <div>
                        <p className='field-kicker'>{t('schedules.active')}</p>
                        <h2>{t('nav.schedules')}</h2>
                    </div>
                    <span className='count-badge'>{schedules.length}</span>
                </div>
                {schedules.length > 0 ? (
                    <ul className='schedule-list'>
                        {schedules.map((schedule) => (
                            <li
                                className='schedule-card'
                                key={schedule.schedule_id}
                            >
                                <div className='schedule-card-top'>
                                    <span className='schedule-icon'>
                                        <CalendarClock
                                            size={16}
                                            aria-hidden='true'
                                        />
                                    </span>
                                    <span
                                        className={`schedule-state ${schedule.enabled ? 'active' : 'paused'}`}
                                    >
                                        {schedule.enabled
                                            ? t('common.enabled')
                                            : t('common.paused')}
                                    </span>
                                </div>
                                <strong className='schedule-tickers'>
                                    {schedule.tickers.join(', ')}
                                </strong>
                                <p className='schedule-when'>
                                    {t('schedules.nextRun', {
                                        time: schedule.run_at.slice(0, 5),
                                    })}
                                    {' · '}
                                    {formatScheduleValue(
                                        locale,
                                        schedule.report_format,
                                    )}
                                </p>
                                <p className='schedule-last-run'>
                                    {t('schedules.lastRun')}:{' '}
                                    {formatRunStatus(
                                        locale,
                                        schedule.last_run_status,
                                    )}
                                </p>
                                <div className='schedule-actions'>
                                    <button
                                        className='button-tertiary'
                                        onClick={() =>
                                            onToggle(
                                                schedule,
                                                !schedule.enabled,
                                            )
                                        }
                                        type='button'
                                    >
                                        {schedule.enabled ? (
                                            <Pause
                                                size={14}
                                                aria-hidden='true'
                                            />
                                        ) : (
                                            <Play
                                                size={14}
                                                aria-hidden='true'
                                            />
                                        )}
                                        {schedule.enabled
                                            ? t('schedules.pause')
                                            : t('schedules.resume')}
                                    </button>
                                    <button
                                        aria-label={`${t('common.delete')} ${schedule.tickers.join(', ')}`}
                                        className='icon-action danger'
                                        onClick={() => onDelete(schedule)}
                                        title={t('common.delete')}
                                        type='button'
                                    >
                                        <Trash2
                                            size={15}
                                            aria-hidden='true'
                                        />
                                    </button>
                                </div>
                            </li>
                        ))}
                    </ul>
                ) : (
                    <div className='empty-state compact'>
                        <span className='empty-mark'>
                            <CalendarClock size={19} aria-hidden='true' />
                        </span>
                        <strong>{t('schedules.empty')}</strong>
                        <p>{t('schedules.emailToSelf')}</p>
                    </div>
                )}
            </section>
        </div>
    );
}
