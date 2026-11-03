
import { useEffect, useId, useRef, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion } from 'motion/react';
import { X } from 'lucide-react';

import type { Locale } from '#/types.js';
import { translate } from '@/features/common/i18n/messages.js';



interface CommandDialogProps {
    isOpen: boolean;
    locale: Locale;
    title: string;
    description: string;
    returnFocusTarget: HTMLElement | null;
    onClose: () => void;
    children: ReactNode;
}


export function CommandDialog({
    isOpen,
    locale,
    title,
    description,
    returnFocusTarget,
    onClose,
    children,
}: CommandDialogProps) {
    const dialogRef = useRef<HTMLElement | null>(null);
    const onCloseRef = useRef(onClose);
    const titleId = useId();
    const descriptionId = useId();
    onCloseRef.current = onClose;

    useEffect(() => {
        if (!isOpen) return;

        const previousFocus =
            returnFocusTarget ??
            (document.activeElement instanceof HTMLElement
                ? document.activeElement
                : null);
        const previousOverflow = document.body.style.overflow;
        document.body.style.overflow = 'hidden';

        const focusFrame = window.requestAnimationFrame(() => {
            const firstField =
                dialogRef.current?.querySelector<HTMLElement>(
                    'input:not([disabled]), select:not([disabled]), textarea:not([disabled])',
                );
            const firstButton =
                dialogRef.current?.querySelector<HTMLElement>(
                    'button:not([disabled])',
                );
            (firstField ?? firstButton ?? dialogRef.current)?.focus();
        });

        const handleKeyDown = (event: KeyboardEvent) => {
            if (event.key === 'Escape') {
                event.preventDefault();
                event.stopPropagation();
                onCloseRef.current();
                return;
            }
            if (event.key !== 'Tab' || !dialogRef.current) {
                return;
            }

            const focusable = Array.from(
                dialogRef.current.querySelectorAll<HTMLElement>(
                    'input:not([disabled]), select:not([disabled]), textarea:not([disabled]), button:not([disabled]), [tabindex="0"]',
                ),
            );
            const first = focusable[0];
            const last = focusable[focusable.length - 1];
            if (!first || !last) {
                event.preventDefault();
                dialogRef.current.focus();
                return;
            }
            if (event.shiftKey && document.activeElement === first) {
                event.preventDefault();
                last.focus();
            } else if (!event.shiftKey && document.activeElement === last) {
                event.preventDefault();
                first.focus();
            }
        };

        document.addEventListener('keydown', handleKeyDown);
        return () => {
            window.cancelAnimationFrame(focusFrame);
            document.removeEventListener('keydown', handleKeyDown);
            document.body.style.overflow = previousOverflow;
            if (previousFocus) {
                window.setTimeout(() => {
                    if (
                        !document.querySelector(
                            '[aria-modal="true"]:not([data-command-dialog])',
                        )
                    ) {
                        previousFocus.focus();
                    }
                }, 190);
            }
        };
    }, [isOpen, returnFocusTarget]);

    return createPortal(
        <AnimatePresence initial={false}>
            {isOpen && (
                <motion.div
                    animate={{ opacity: 1 }}
                    className='command-dialog-backdrop'
                    exit={{ opacity: 0 }}
                    initial={{ opacity: 0 }}
                    key='command-dialog'
                    onMouseDown={(event) => {
                        if (event.target === event.currentTarget) {
                            onCloseRef.current();
                        }
                    }}
                    transition={{ duration: 0.16, ease: 'easeOut' }}
                >
                    <motion.section
                        animate={{ opacity: 1, scale: 1, y: 0 }}
                        aria-describedby={descriptionId}
                        aria-labelledby={titleId}
                        aria-modal='true'
                        className='command-dialog-panel'
                        data-command-dialog=''
                        exit={{ opacity: 0, scale: 0.98, y: 10 }}
                        initial={{ opacity: 0, scale: 0.98, y: 10 }}
                        ref={dialogRef}
                        role='dialog'
                        tabIndex={-1}
                        transition={{
                            type: 'spring',
                            stiffness: 360,
                            damping: 30,
                        }}
                    >
                        <header className='command-dialog-header'>
                            <div>
                                <p className='command-dialog-kicker'>
                                    {translate(locale, 'command.quoteLabel')}
                                </p>
                                <h2 id={titleId}>{title}</h2>
                                <p id={descriptionId}>{description}</p>
                            </div>
                            <button
                                aria-label={translate(locale, 'common.close')}
                                className='command-dialog-close'
                                onClick={onClose}
                                type='button'
                            >
                                <X size={17} aria-hidden='true' />
                            </button>
                        </header>
                        <div className='command-dialog-body'>{children}</div>
                    </motion.section>
                </motion.div>
            )}
        </AnimatePresence>,
        document.body,
    );
}
