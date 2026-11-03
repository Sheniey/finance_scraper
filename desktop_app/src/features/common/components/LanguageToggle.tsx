
import { useEffect, useRef } from 'react';
import { Check, ChevronDown, Languages } from 'lucide-react';

import type { Locale } from '#/types.js';
import {
    getLocaleName,
    localeOptions,
    translate,
} from '@/features/common/i18n/messages.js';



interface LanguageToggleProps {
    locale: Locale;
    onLocaleChange: (locale: Locale) => void;
}


export function LanguageToggle({
    locale,
    onLocaleChange,
}: LanguageToggleProps) {
    const menuRef = useRef<HTMLDetailsElement>(null);
    const languageLabel = translate(locale, 'common.language');
    const selectedLanguageName = getLocaleName(locale);

    useEffect(() => {
        const closeOnOutsidePointerDown = (event: PointerEvent) => {
            const menu = menuRef.current;
            if (
                menu &&
                event.target instanceof Node &&
                !menu.contains(event.target)
            ) {
                menu.open = false;
            }
        };
        const closeOnEscape = (event: KeyboardEvent) => {
            const menu = menuRef.current;
            if (event.key === 'Escape' && menu?.open) {
                menu.open = false;
                menu.querySelector('summary')?.focus();
            }
        };

        document.addEventListener('pointerdown', closeOnOutsidePointerDown);
        document.addEventListener('keydown', closeOnEscape);
        return () => {
            document.removeEventListener(
                'pointerdown',
                closeOnOutsidePointerDown,
            );
            document.removeEventListener('keydown', closeOnEscape);
        };
    }, []);

    return (
        <details className='language-menu' ref={menuRef}>
            <summary
                aria-label={`${languageLabel}: ${selectedLanguageName}`}
                className='language-menu-trigger'
            >
                <span className='language-menu-code'>{locale.toUpperCase()}</span>
                <Languages
                    aria-hidden='true'
                    className='language-menu-languages'
                    size={12}
                    strokeWidth={1.8}
                />
                <ChevronDown
                    aria-hidden='true'
                    className='language-menu-chevron'
                    size={12}
                    strokeWidth={1.8}
                />
            </summary>
            <div
                aria-label={languageLabel}
                className='language-menu-popover'
                role='group'
            >
                {localeOptions.map(({ locale: optionLocale, code, name }) => {
                    const isSelected = optionLocale === locale;
                    return (
                        <button
                            aria-pressed={isSelected}
                            className='language-menu-option'
                            key={optionLocale}
                            lang={optionLocale}
                            onClick={() => {
                                onLocaleChange(optionLocale);
                                if (menuRef.current) menuRef.current.open = false;
                            }}
                            type='button'
                        >
                            <span className='language-menu-option-code'>
                                {code}
                            </span>
                            <span className='language-menu-option-name'>
                                {name}
                            </span>
                            {isSelected && (
                                <Check
                                    aria-hidden='true'
                                    className='language-menu-check'
                                    size={15}
                                />
                            )}
                        </button>
                    );
                })}
            </div>
        </details>
    );
}
