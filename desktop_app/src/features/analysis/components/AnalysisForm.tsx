
import type { FormEvent } from 'react';
import { motion } from 'motion/react';
import {
    BarChart3,
    BrainCircuit,
    FileOutput,
    Sparkles,
} from 'lucide-react';

import type { Locale, ReportFormat } from '#/types.js';
import { LoadingSpinner } from '@/features/common/components/LoadingSpinner.js';
import { translate } from '@/features/common/i18n/messages.js';
import { CustomReportBuilder } from '@/features/analysis/components/CustomReportBuilder.js';
import type {
    AnalysisMode,
    CustomReportSection,
} from '@/features/analysis/types/index.js';
import {
    analysisModes,
    outputFormats,
} from '@/features/analysis/lib/analysis-utils.js';



interface AnalysisFormProps {
    locale: Locale;
    ticker: string;
    reportName: string;
    format: ReportFormat;
    mode: AnalysisMode;
    customSections: CustomReportSection[];
    horizon: number;
    explain: boolean;
    charts: boolean;
    aiAvailable: boolean;
    isSavingPreference: boolean;
    preferenceSaved: boolean;
    isSubmitting: boolean;
    error: string | null;
    onTickerChange: (value: string) => void;
    onReportNameChange: (value: string) => void;
    onFormatChange: (value: ReportFormat) => void;
    onModeChange: (value: AnalysisMode) => void;
    onCustomSectionsChange: (value: CustomReportSection[]) => void;
    onCustomSectionsSave: () => void;
    onHorizonChange: (value: number) => void;
    onExplainChange: (value: boolean) => void;
    onChartsChange: (value: boolean) => void;
    onSubmit: (event: FormEvent<HTMLFormElement>) => void;
}


export function AnalysisForm({
    locale,
    ticker,
    reportName,
    format,
    mode,
    customSections,
    horizon,
    explain,
    charts,
    aiAvailable,
    isSavingPreference,
    preferenceSaved,
    isSubmitting,
    error,
    onTickerChange,
    onReportNameChange,
    onFormatChange,
    onModeChange,
    onCustomSectionsChange,
    onCustomSectionsSave,
    onHorizonChange,
    onExplainChange,
    onChartsChange,
    onSubmit,
}: AnalysisFormProps) {
    const t = (key: string) => translate(locale, key);

    return (
        <form className='content-panel analysis-form' onSubmit={onSubmit}>
            <div className='panel-heading-row'>
                <div>
                    <p className='field-kicker'>{t('analysis.formLabel')}</p>
                    <h2>{t('analysis.formTitle')}</h2>
                </div>
                <span className='panel-symbol'>
                    <Sparkles size={18} aria-hidden='true' />
                </span>
            </div>
            <label className='form-field ticker-field'>
                <span>{t('analysis.ticker')}</span>
                <input
                    autoCapitalize='characters'
                    autoComplete='off'
                    maxLength={20}
                    onChange={(event) =>
                        onTickerChange(event.target.value.toUpperCase())
                    }
                    placeholder={t('analysis.tickerPlaceholder')}
                    required
                    value={ticker}
                />
                <small>{t('analysis.tickerHint')}</small>
            </label>

            <label className='form-field'>
                <span>{t('analysis.reportName')}</span>
                <input
                    autoComplete='off'
                    maxLength={80}
                    onChange={(event) =>
                        onReportNameChange(event.target.value)
                    }
                    placeholder={t('analysis.reportNamePlaceholder')}
                    value={reportName}
                />
                <small>{t('analysis.reportNameHint')}</small>
            </label>

            <div className='form-grid two-column'>
                <label className='form-field'>
                    <span>{t('analysis.format')}</span>
                    <select
                        onChange={(event) =>
                            onFormatChange(event.target.value as ReportFormat)
                        }
                        value={format}
                    >
                        {outputFormats.map((item) => (
                            <option key={item} value={item}>
                                {translate(locale, `email.${item}`)}
                            </option>
                        ))}
                    </select>
                </label>
                <label className='form-field'>
                    <span>{t('analysis.mode')}</span>
                    <select
                        onChange={(event) =>
                            onModeChange(event.target.value as AnalysisMode)
                        }
                        value={mode}
                    >
                        {analysisModes.map((item) => (
                            <option key={item} value={item}>
                                {t(`analysis.modes.${item}`)}
                            </option>
                        ))}
                    </select>
                </label>
            </div>

            {mode === 'custom' && (
                <CustomReportBuilder
                    aiAvailable={aiAvailable}
                    isSaved={preferenceSaved}
                    isSaving={isSavingPreference}
                    locale={locale}
                    onChange={onCustomSectionsChange}
                    onSave={onCustomSectionsSave}
                    sections={customSections}
                />
            )}

            <label className='form-field horizon-field'>
                <span>{t('analysis.horizon')}</span>
                <input
                    max={365}
                    min={1}
                    onChange={(event) =>
                        onHorizonChange(Number(event.target.value))
                    }
                    type='number'
                    value={horizon}
                />
            </label>
            {mode !== 'custom' && (
                <>
                    <motion.label
                        animate={{
                            backgroundColor: explain ? '#f5faf8' : '#ffffff',
                            borderColor: explain
                                ? 'rgba(36, 122, 119, 0.28)'
                                : 'rgba(13, 23, 38, 0.08)',
                        }}
                        className={`choice-row ${!aiAvailable ? 'locked' : ''}`}
                        initial={false}
                        transition={{ duration: 0.15, ease: 'easeOut' }}
                        whileTap={{ scale: 0.992 }}
                    >
                        <span className='choice-icon'>
                            <BrainCircuit size={17} aria-hidden='true' />
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
                            onChange={(event) =>
                                onExplainChange(event.target.checked)
                            }
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
                            <BarChart3 size={17} aria-hidden='true' />
                        </span>
                        <span className='choice-copy'>
                            <strong>{t('analysis.charts')}</strong>
                            <small>{t('analysis.chartsCopy')}</small>
                        </span>
                        <input
                            checked={charts}
                            onChange={(event) =>
                                onChartsChange(event.target.checked)
                            }
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
                </>
            )}

            {error && (
                <p className='form-message error-message' role='alert'>
                    {error}
                </p>
            )}
            <button
                className='button-primary form-primary'
                disabled={isSubmitting}
                type='submit'
            >
                {isSubmitting ? (
                    <LoadingSpinner size={17} />
                ) : (
                    <FileOutput size={17} aria-hidden='true' />
                )}
                {isSubmitting
                    ? t('analysis.generating')
                    : t('analysis.generate')}
            </button>
        </form>
    );
}
