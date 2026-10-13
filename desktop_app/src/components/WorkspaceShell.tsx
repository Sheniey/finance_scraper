import type { ReactNode } from 'react';
import {
    Activity,
    CalendarClock,
    FileText,
    House,
    Languages,
    LineChart,
    LogOut,
    Settings2,
    Sparkles,
} from 'lucide-react';

import type {
    ApiStatus,
    DashboardView,
    Locale,
    UserProfile,
} from '#/types.js';
import { translate } from '@/i18n/messages.js';

interface WorkspaceShellProps {
    activeView: DashboardView;
    apiStatus: ApiStatus;
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
    icon: typeof House;
}> = [
    { view: 'overview', key: 'nav.overview', icon: House },
    { view: 'analysis', key: 'nav.analysis', icon: Sparkles },
    { view: 'reports', key: 'nav.reports', icon: FileText },
    { view: 'watchlist', key: 'nav.watchlist', icon: LineChart },
    { view: 'schedules', key: 'nav.schedules', icon: CalendarClock },
];

export function WorkspaceShell({
    activeView,
    apiStatus,
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
        navigation.find((item) => item.view === activeView)?.key ??
            'nav.settings',
    );
    const initials = profile.name
        .split(/\s+/)
        .filter(Boolean)
        .slice(0, 2)
        .map((part) => part[0]?.toUpperCase())
        .join('');
    const dateLabel = new Intl.DateTimeFormat(
        locale === 'es' ? 'es-MX' : 'en-US',
        {
            weekday: 'long',
            month: 'short',
            day: 'numeric',
        },
    ).format(new Date());
    const apiOnline = apiStatus.state === 'online';

    return (
        <div className='workspace-shell'>
            <aside className='workspace-sidebar'>
                <div className='sidebar-brand'>
                    <span className='sidebar-brand-mark'>
                        <img src='/icons/favicon.svg' alt='' />
                    </span>
                    <span>
                        <strong>{t('brand.name')}</strong>
                        <small>{t('brand.tagline')}</small>
                    </span>
                </div>

                <div className='workspace-switcher'>
                    <span className='workspace-monogram'>FS</span>
                    <span className='workspace-switcher-copy'>
                        <small>{t('nav.workspace')}</small>
                        <strong>{profile.name}</strong>
                    </span>
                    <Activity size={15} aria-hidden='true' />
                </div>

                <nav className='workspace-nav' aria-label={t('nav.workspace')}>
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
                </nav>

                <div className='sidebar-bottom'>
                    <div
                        aria-live='polite'
                        className={`api-health-card ${apiOnline ? 'online' : 'offline'}`}
                        role='status'
                    >
                        <span className='health-dot' aria-hidden='true' />
                        <span className='api-health-copy'>
                            <strong>
                                {apiOnline
                                    ? t('common.workspaceReady')
                                    : apiStatus.state === 'starting'
                                        ? t('common.workspaceStarting')
                                        : t('common.apiError')}
                            </strong>
                        </span>
                    </div>
                    <div className='sidebar-user'>
                        <span className='avatar'>{initials || 'FS'}</span>
                        <span className='sidebar-user-copy'>
                            <strong>{profile.name}</strong>
                            <small>{profile.email}</small>
                        </span>
                        <button
                            aria-label={t('nav.signOut')}
                            className='sign-out-button'
                            onClick={onLogout}
                            title={t('nav.signOut')}
                            type='button'
                        >
                            <LogOut size={16} aria-hidden='true' />
                        </button>
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
                        <label className='language-switch light'>
                            <Languages size={15} aria-hidden='true' />
                            <span className='sr-only'>{t('common.language')}</span>
                            <select
                                aria-label={t('common.language')}
                                onChange={(event) =>
                                    onLocaleChange(event.target.value as Locale)
                                }
                                value={locale}
                            >
                                <option value='es'>ES</option>
                                <option value='en'>EN</option>
                            </select>
                        </label>
                    </div>
                </header>
                <div className='workspace-content'>{children}</div>
            </main>
        </div>
    );
}
