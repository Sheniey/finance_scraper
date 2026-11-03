
import { useEffect, useRef, useState, type ReactNode } from 'react';
import { AnimatePresence, motion } from 'motion/react';
import {
    BarChart3,
    BrainCircuit,
    BriefcaseBusiness,
    CalendarClock,
    ChevronDown,
    LineChart,
    LogOut,
    Settings2,
} from 'lucide-react';

import type {
    DashboardView,
    Locale,
    UserProfile,
} from '#/types.js';
import { getIntlLocale, translate } from '@/features/common/i18n/messages.js';
import { LanguageToggle } from '@/features/common/components/LanguageToggle.js';



interface WorkspaceShellProps {
    activeView: DashboardView;
    locale: Locale;
    profile: UserProfile;
    onLogout: () => void;
    onNavigate: (view: DashboardView) => void;
    onLocaleChange: (locale: Locale) => void;
    children: ReactNode;
}


const navigation: Array<{
    view: DashboardView;
    key: string;
    icon: typeof BarChart3;
}> = [
    { view: 'overview', key: 'nav.reports', icon: BarChart3 },
    { view: 'watchlist', key: 'nav.watchlist', icon: LineChart },
    { view: 'portfolio', key: 'nav.portfolio', icon: BriefcaseBusiness },
    { view: 'schedules', key: 'nav.schedules', icon: CalendarClock },
];


export function WorkspaceShell({
    activeView,
    locale,
    profile,
    onLogout,
    onNavigate,
    onLocaleChange,
    children,
}: WorkspaceShellProps) {
    const t = (key: string, values?: Record<string, string | number>) =>
        translate(locale, key, values);
    const pageTitle = t(
        activeView === 'aiProviders'
            ? 'nav.aiProviders'
            : navigation.find((item) => item.view === activeView)?.key ??
                  'nav.settings',
    );
    const initials = profile.name
        .split(/\s+/)
        .filter(Boolean)
        .slice(0, 2)
        .map((part) => part[0]?.toUpperCase())
        .join('');
    const dateLabel = new Intl.DateTimeFormat(
        getIntlLocale(locale),
        {
            weekday: 'long',
            month: 'short',
            day: 'numeric',
        },
    ).format(new Date());
    const [isUserMenuOpen, setIsUserMenuOpen] = useState(false);
    const userMenuRef = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (!isUserMenuOpen) {
            return;
        }

        const closeOnOutsidePointerDown = (event: PointerEvent) => {
            if (
                event.target instanceof Node &&
                !userMenuRef.current?.contains(event.target)
            ) {
                setIsUserMenuOpen(false);
            }
        };
        const closeOnEscape = (event: KeyboardEvent) => {
            if (event.key === 'Escape') {
                setIsUserMenuOpen(false);
                userMenuRef.current
                    ?.querySelector<HTMLButtonElement>(
                        '.sidebar-user-trigger',
                    )
                    ?.focus();
            }
        };

        document.addEventListener(
            'pointerdown',
            closeOnOutsidePointerDown,
            true,
        );
        document.addEventListener('keydown', closeOnEscape);
        return () => {
            document.removeEventListener(
                'pointerdown',
                closeOnOutsidePointerDown,
                true,
            );
            document.removeEventListener('keydown', closeOnEscape);
        };
    }, [isUserMenuOpen]);

    return (
        <div className='workspace-shell'>
            <aside className='workspace-sidebar'>
                <div className='sidebar-brand'>
                    <span className='sidebar-brand-mark'>
                        <img src='/icons/favicon.svg' alt='' />
                    </span>
                    <span>
                        <strong>{t('brand.name', { app_name: APP_NAME })}</strong>
                    </span>
                </div>

                <nav className='workspace-nav pt-6' aria-label={t('nav.workspace')}>
                    <p className='nav-section-label'>{t('nav.workspace')}</p>
                    {navigation.map(({ view, key, icon: Icon }) => (
                        <button
                            aria-current={activeView === view ? 'page' : undefined}
                            className={`workspace-nav-item ${activeView === view ? 'active' : ''}`}
                            key={view}
                            onClick={() => onNavigate(view)}
                            type='button'
                        >
                            <Icon size={17} strokeWidth={1.8} aria-hidden='true' />
                            <span>{t(key)}</span>
                        </button>
                    ))}
                    <p className='nav-section-label nav-section-spaced'>
                        {t('nav.system')}
                    </p>
                    <button
                        aria-current={activeView === 'settings' ? 'page' : undefined}
                        className={`workspace-nav-item ${activeView === 'settings' ? 'active' : ''}`}
                        onClick={() => onNavigate('settings')}
                        type='button'
                    >
                        <Settings2 size={17} strokeWidth={1.8} aria-hidden='true' />
                        <span>{t('nav.settings')}</span>
                    </button>
                    <button
                        aria-current={activeView === 'aiProviders' ? 'page' : undefined}
                        className={`workspace-nav-item ${activeView === 'aiProviders' ? 'active' : ''}`}
                        onClick={() => onNavigate('aiProviders')}
                        type='button'
                    >
                        <BrainCircuit
                            size={17}
                            strokeWidth={1.8}
                            aria-hidden='true'
                        />
                        <span>{t('nav.aiProviders')}</span>
                    </button>
                </nav>

                <div className='sidebar-bottom'>
                    <div className='sidebar-user' ref={userMenuRef}>
                        <motion.button
                            aria-expanded={isUserMenuOpen}
                            aria-haspopup='menu'
                            className='sidebar-user-trigger'
                            onClick={() =>
                                setIsUserMenuOpen((isOpen) => !isOpen)
                            }
                            type='button'
                            whileTap={{ scale: 0.98 }}
                        >
                            <span className='avatar'>{initials || 'FS'}</span>
                            <span className='sidebar-user-copy'>
                                <strong>{profile.name}</strong>
                                <small>{profile.email}</small>
                            </span>
                            <ChevronDown
                                aria-hidden='true'
                                className={`sidebar-user-chevron ${isUserMenuOpen ? 'open' : ''}`}
                                size={14}
                            />
                        </motion.button>
                        <AnimatePresence>
                            {isUserMenuOpen && (
                                <motion.div
                                    animate={{ opacity: 1, scale: 1, x: 0 }}
                                    aria-label={profile.name}
                                    className='sidebar-user-menu'
                                    exit={{ opacity: 0, scale: 0.97, x: -5 }}
                                    initial={{ opacity: 0, scale: 0.97, x: -5 }}
                                    role='menu'
                                    transition={{
                                        type: 'spring',
                                        stiffness: 420,
                                        damping: 32,
                                    }}
                                >
                                    <div className='sidebar-user-menu-profile'>
                                        <strong>{profile.name}</strong>
                                        <small>{profile.email}</small>
                                    </div>
                                    <button
                                        className='sidebar-user-menu-action'
                                        onClick={() => {
                                            setIsUserMenuOpen(false);
                                            onLogout();
                                        }}
                                        role='menuitem'
                                        type='button'
                                    >
                                        <LogOut size={16} aria-hidden='true' />
                                        {t('nav.signOut')}
                                    </button>
                                </motion.div>
                            )}
                        </AnimatePresence>
                    </div>
                </div>
            </aside>

            <main className='workspace-main' id='main-content' tabIndex={-1}>
                <header className='workspace-topbar'>
                    <div className='page-breadcrumb'>
                        <span>{t('nav.workspace')}</span>
                        <span aria-hidden='true'>/</span>
                        <strong>{pageTitle}</strong>
                    </div>
                    <div className='topbar-actions'>
                        <time className='date-label'>{dateLabel}</time>
                        <LanguageToggle locale={locale} onLocaleChange={onLocaleChange} />
                    </div>
                </header>
                <div className='workspace-content'>
                    <AnimatePresence initial={false} mode='wait'>
                        <motion.div
                            animate={{ opacity: 1, y: 0 }}
                            className='workspace-view-transition'
                            exit={{ opacity: 0, y: -4 }}
                            initial={{ opacity: 0, y: 7 }}
                            key={activeView}
                            transition={{ duration: 0.15, ease: 'easeOut' }}
                        >
                            {children}
                        </motion.div>
                    </AnimatePresence>
                </div>
            </main>
        </div>
    );
}
