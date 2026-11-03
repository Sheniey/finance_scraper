
import { useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { AnimatePresence, motion } from 'motion/react';
import type { ResourceContextAction } from '@/features/command-palette/types/index.js';


interface ResourceContextMenuProps {
    isOpen: boolean;
    label: string;
    actions: ResourceContextAction[];
    position: { x: number; y: number };
    focusFirstItem?: boolean;
    returnFocusTarget?: HTMLElement | null;
    onClose: () => void;
    onMouseEnter?: () => void;
    onMouseLeave?: () => void;
}

export function ResourceContextMenu({
    isOpen,
    label,
    actions,
    position: anchor,
    focusFirstItem = false,
    returnFocusTarget,
    onClose,
    onMouseEnter,
    onMouseLeave,
}: ResourceContextMenuProps) {
    const menuRef = useRef<HTMLDivElement>(null);
    const onCloseRef = useRef(onClose);
    const [position, setPosition] = useState(anchor);
    onCloseRef.current = onClose;

    useLayoutEffect(() => {
        if (!isOpen || !menuRef.current) {
            return;
        }
        const { width, height } = menuRef.current.getBoundingClientRect();
        setPosition({
            x: Math.max(8, Math.min(anchor.x, window.innerWidth - width - 8)),
            y: Math.max(8, Math.min(anchor.y, window.innerHeight - height - 8)),
        });
    }, [actions.length, anchor.x, anchor.y, isOpen]);

    useLayoutEffect(() => {
        if (!isOpen) return;

        const focusFrame = focusFirstItem
            ? window.requestAnimationFrame(() =>
                  menuRef.current
                      ?.querySelector<HTMLButtonElement>(
                          'button:not(:disabled)',
                      )
                      ?.focus(),
              )
            : null;
        const closeOnOutsidePointerDown = (event: PointerEvent) => {
            if (
                event.target instanceof Element &&
                event.target.closest('[data-resource-context-trigger]')
            ) {
                return;
            }
            
            if (
                event.target instanceof Node &&
                !menuRef.current?.contains(event.target)
            ) {
                onCloseRef.current();
            }
        };
        const handleMenuKeys = (event: KeyboardEvent) => {
            if (event.key === 'Escape') {
                event.preventDefault();
                onCloseRef.current();
                returnFocusTarget?.focus();
                return;
            }
            if (event.key !== 'ArrowDown' && event.key !== 'ArrowUp') {
                return;
            }

            const items = Array.from(
                menuRef.current?.querySelectorAll<HTMLButtonElement>(
                    'button:not(:disabled)',
                ) ?? [],
            );
            if (items.length === 0) {
                return;
            }
            event.preventDefault();
            const currentIndex = items.findIndex(
                (item) => item === document.activeElement,
            );
            const direction = event.key === 'ArrowDown' ? 1 : -1;
            const nextIndex =
                currentIndex < 0
                    ? direction > 0
                        ? 0
                        : items.length - 1
                    : (currentIndex + direction + items.length) % items.length;
            items[nextIndex]?.focus();
        };
        const closeOnViewportChange = () => onCloseRef.current();

        document.addEventListener(
            'pointerdown',
            closeOnOutsidePointerDown,
            true,
        );
        document.addEventListener('keydown', handleMenuKeys);
        window.addEventListener('resize', closeOnViewportChange);
        window.addEventListener('scroll', closeOnViewportChange, true);
        return () => {
            if (focusFrame !== null) {
                window.cancelAnimationFrame(focusFrame);
            }
            document.removeEventListener(
                'pointerdown',
                closeOnOutsidePointerDown,
                true,
            );
            document.removeEventListener('keydown', handleMenuKeys);
            window.removeEventListener('resize', closeOnViewportChange);
            window.removeEventListener(
                'scroll',
                closeOnViewportChange,
                true,
            );
        };
    }, [focusFirstItem, isOpen, returnFocusTarget]);

    const origin =
        position.x > window.innerWidth / 2 ? 'right top' : 'left top';

    return createPortal(
        <AnimatePresence initial={false}>
            {isOpen && (
                <motion.div
                    animate={{ opacity: 1, scale: 1 }}
                    aria-label={label}
                    className='resource-context-menu'
                    data-resource-context-menu=''
                    exit={{ opacity: 0, scale: 0.97 }}
                    initial={{ opacity: 0, scale: 0.97 }}
                    key='resource-context-menu'
                    onMouseEnter={onMouseEnter}
                    onMouseLeave={onMouseLeave}
                    ref={menuRef}
                    role='menu'
                    style={{
                        left: position.x,
                        top: position.y,
                        transformOrigin: origin,
                    }}
                    transition={{ duration: 0.14, ease: 'easeOut' }}
                >
                    {actions.map((action) => {
                        const Icon = action.icon;
                        return (
                            <motion.button
                                className={[
                                    action.danger ? 'danger' : '',
                                    action.separatorBefore
                                        ? 'has-separator'
                                        : '',
                                ]
                                    .filter(Boolean)
                                    .join(' ')}
                                disabled={action.disabled}
                                key={action.id}
                                onClick={() => {
                                    void action.onSelect();
                                    onClose();
                                }}
                                role='menuitem'
                                type='button'
                                whileTap={{ scale: 0.985 }}
                            >
                                {action.separatorBefore && (
                                    <span
                                        aria-hidden='true'
                                        className='resource-menu-separator'
                                    />
                                )}
                                <Icon size={15} aria-hidden='true' />
                                <span>{action.label}</span>
                            </motion.button>
                        );
                    })}
                </motion.div>
            )}
        </AnimatePresence>,
        document.body,
    );
}
