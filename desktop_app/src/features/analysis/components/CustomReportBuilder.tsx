
import { useRef, useState } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import { Check, ChevronDown, ChevronUp, GripVertical } from 'lucide-react';

import type { Locale } from '#/types.js';
import { translate } from '@/features/common/i18n/messages.js';
import type { CustomReportSection } from '@/features/analysis/types/index.js';
import {
    customReportSectionOptions,
} from '@/features/analysis/lib/analysis-utils.js';



interface CustomReportBuilderProps {
    locale: Locale;
    sections: CustomReportSection[];
    aiAvailable: boolean;
    isSaving: boolean;
    isSaved: boolean;
    onChange: (sections: CustomReportSection[]) => void;
    onSave: () => void;
}


export function CustomReportBuilder({
    locale,
    sections,
    aiAvailable,
    isSaving,
    isSaved,
    onChange,
    onSave,
}: CustomReportBuilderProps) {
    const [draggingSection, setDraggingSection] =
        useState<CustomReportSection | null>(null);
    const draggingSectionRef = useRef<CustomReportSection | null>(null);
    const t = (key: string, values?: Record<string, string | number>) =>
        translate(locale, key, values);

    const displaySections = [...customReportSectionOptions].sort(
        (left, right) => {
            const leftIndex = sections.indexOf(left.id);
            const rightIndex = sections.indexOf(right.id);
            if (leftIndex >= 0 && rightIndex >= 0) {
                return leftIndex - rightIndex;
            }
            if (leftIndex >= 0) {
                return -1;
            }
            if (rightIndex >= 0) {
                return 1;
            }
            return 0;
        },
    );

    function toggleSection(section: CustomReportSection, checked: boolean) {
        if (checked) {
            onChange([...sections, section]);
            return;
        }
        onChange(sections.filter((current) => current !== section));
    }

    function moveSection(
        section: CustomReportSection,
        direction: -1 | 1,
    ) {
        const sourceIndex = sections.indexOf(section);
        const destinationIndex = sourceIndex + direction;
        if (
            sourceIndex < 0 ||
            destinationIndex < 0 ||
            destinationIndex >= sections.length
        ) {
            return;
        }
        const reordered = [...sections];
        const movedSection = reordered.splice(sourceIndex, 1)[0];
        if (!movedSection) {
            return;
        }
        reordered.splice(destinationIndex, 0, movedSection);
        onChange(reordered);
    }

    function dropOn(target: CustomReportSection) {
        const dragged = draggingSectionRef.current;
        if (dragged === null) {
            return;
        }
        const sourceIndex = sections.indexOf(dragged);
        const targetIndex = sections.indexOf(target);
        if (sourceIndex < 0 || targetIndex < 0) {
            return;
        }
        const reordered = [...sections];
        const movedSection = reordered.splice(sourceIndex, 1)[0];
        if (!movedSection) {
            return;
        }
        reordered.splice(targetIndex, 0, movedSection);
        onChange(reordered);
    }

    return (
        <section
            aria-labelledby='custom-report-builder-title'
            className='custom-report-builder'
        >
            <div className='custom-report-builder-heading'>
                <div>
                    <p className='field-kicker'>{t('analysis.customBuilder')}</p>
                    <h3 id='custom-report-builder-title'>
                        {t('analysis.customBuilderTitle')}
                    </h3>
                    <p>{t('analysis.customBuilderCopy')}</p>
                </div>
                <span className='custom-section-count'>
                    {t('analysis.selectedSections', {
                        count: sections.length,
                    })}
                </span>
            </div>

            <ol className='custom-report-section-list'>
                {displaySections.map(({ id, labelKey }) => {
                    const selected = sections.includes(id);
                    const isLocked = id === 'explanation' && !aiAvailable;
                    const sectionLabel = t(labelKey);
                    return (
                        <li
                            className={`custom-report-section ${selected ? 'selected' : ''} ${draggingSection === id ? 'dragging' : ''}`}
                            draggable={selected}
                            key={id}
                            onDragEnd={() => {
                                draggingSectionRef.current = null;
                                setDraggingSection(null);
                            }}
                            onDragOver={(event) => {
                                if (selected && draggingSectionRef.current) {
                                    event.preventDefault();
                                }
                            }}
                            onDrop={(event) => {
                                event.preventDefault();
                                dropOn(id);
                                draggingSectionRef.current = null;
                                setDraggingSection(null);
                            }}
                            onDragStart={(event) => {
                                if (!selected) {
                                    event.preventDefault();
                                    return;
                                }
                                draggingSectionRef.current = id;
                                setDraggingSection(id);
                                event.dataTransfer.effectAllowed = 'move';
                                event.dataTransfer.setData('text/plain', id);
                            }}
                        >
                            <label className='custom-report-section-label'>
                                <input
                                    className='sr-only'
                                    checked={selected}
                                    disabled={isLocked && !selected}
                                    onChange={(event) =>
                                        toggleSection(id, event.target.checked)
                                    }
                                    type='checkbox'
                                />
                                <motion.span
                                    animate={{
                                        backgroundColor: selected
                                            ? '#247a77'
                                            : '#ffffff',
                                        borderColor: selected
                                            ? '#247a77'
                                            : '#c4cdd0',
                                        scale: selected ? 1 : 0.96,
                                    }}
                                    aria-hidden='true'
                                    className='custom-section-check'
                                    initial={false}
                                    transition={{
                                        type: 'spring',
                                        stiffness: 480,
                                        damping: 32,
                                    }}
                                >
                                    <AnimatePresence initial={false}>
                                        {selected && (
                                            <motion.span
                                                animate={{
                                                    opacity: 1,
                                                    rotate: 0,
                                                    scale: 1,
                                                }}
                                                exit={{
                                                    opacity: 0,
                                                    rotate: -20,
                                                    scale: 0.7,
                                                }}
                                                initial={{
                                                    opacity: 0,
                                                    rotate: 20,
                                                    scale: 0.7,
                                                }}
                                                transition={{
                                                    duration: 0.14,
                                                    ease: 'easeOut',
                                                }}
                                            >
                                                <Check
                                                    size={12}
                                                    strokeWidth={3}
                                                />
                                            </motion.span>
                                        )}
                                    </AnimatePresence>
                                </motion.span>
                                <span className='custom-section-copy'>
                                    <strong>{sectionLabel}</strong>
                                    {id === 'explanation' && !aiAvailable && (
                                        <small>{t('analysis.aiUnavailable')}</small>
                                    )}
                                </span>
                            </label>
                            {selected && (
                                <span className='custom-section-order'>
                                    <button
                                        aria-label={t(
                                            'analysis.moveSectionUp',
                                            { section: sectionLabel },
                                        )}
                                        disabled={sections[0] === id}
                                        onClick={() => moveSection(id, -1)}
                                        type='button'
                                    >
                                        <ChevronUp size={15} aria-hidden='true' />
                                    </button>
                                    <button
                                        aria-label={t(
                                            'analysis.moveSectionDown',
                                            { section: sectionLabel },
                                        )}
                                        disabled={sections.at(-1) === id}
                                        onClick={() => moveSection(id, 1)}
                                        type='button'
                                    >
                                        <ChevronDown size={15} aria-hidden='true' />
                                    </button>
                                    <span
                                        aria-hidden='true'
                                        className='custom-section-grip'
                                        title={t('analysis.dragToReorder')}
                                    >
                                        <GripVertical size={16} />
                                    </span>
                                </span>
                            )}
                        </li>
                    );
                })}
            </ol>
            <p className='custom-report-builder-hint'>
                {t('analysis.dragToReorder')}
            </p>
            <div className='custom-report-builder-footer'>
                {isSaved && (
                    <span role='status'>{t('analysis.preferenceSaved')}</span>
                )}
                <button
                    className='button-secondary'
                    disabled={isSaving || sections.length === 0}
                    onClick={onSave}
                    type='button'
                >
                    {isSaving
                        ? t('analysis.savingPreference')
                        : t('analysis.savePreference')}
                </button>
            </div>
        </section>
    );
}
