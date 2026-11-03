
import {
    useCallback,
    useEffect,
    useMemo,
    useRef,
    useState,
    type KeyboardEvent as ReactKeyboardEvent,
} from 'react';
import { createPortal } from 'react-dom';
import { fuzzyFilter, type CommandOption } from 'kmenu';
import { AnimatePresence, motion } from 'motion/react';
import {
    BarChart3,
    BrainCircuit,
    BriefcaseBusiness,
    CalendarClock,
    Cpu,
    Download,
    FileText,
    KeyRound,
    Languages,
    LineChart,
    Mail,
    Plus,
    Search,
    Settings2,
} from 'lucide-react';

import type {
    CreateReportRequest,
    DashboardView,
    GoogleAccountStatus,
    Locale,
    ReportEntry,
    UserProfile,
} from '#/types.js';
import type { ToastKind } from '@/features/common/types/index.js';
import { translate } from '@/features/common/i18n/messages.js';
import { ConfigureApiKeys } from '@/features/ai-providers/commands/ConfigureApiKeys.js';
import { OllamaAction } from '@/features/ai-providers/commands/OllamaAction.js';
import { CreateReportCommand } from '@/features/reports/commands/CreateReport.js';
import { ChangeLanguage } from '@/features/settings/commands/ChangeLanguage.js';
import { AddWatchlistTicker } from '@/features/watchlist/commands/AddWatchlistTicker.js';
import { AddPortfolioTrade } from '@/features/portfolio/commands/AddPortfolioTrade.js';
import { ConnectGoogle } from '@/features/schedules/commands/ConnectGoogle.js';
import type {
    PaletteCommandData,
    PaletteDialog,
} from '@/features/command-palette/types/index.js';
import '@/features/command-palette/styles/command-palette.css';



interface CommandPaletteProps {
    locale: Locale;
    profile: UserProfile;
    onNavigate: (view: DashboardView) => void;
    onLocaleChange: (locale: Locale) => Promise<boolean>;
    onProfileChange: (profile: UserProfile) => Promise<void>;
    onPortfolioChanged: () => void;
    googleStatus: GoogleAccountStatus | null;
    onSchedulesChanged: () => Promise<void>;
    onExportAllReports: () => Promise<void>;
    onReportCreate: (request: CreateReportRequest) => Promise<ReportEntry>;
    onReportOpen: (report: ReportEntry) => Promise<void>;
    onReportsChanged: () => Promise<unknown>;
    onCustomReportSave: (sections: string[]) => Promise<void>;
    onNotify: (message: string, kind?: ToastKind) => void;
}


const isEditableTarget = (target: EventTarget | null): boolean => {
    return (
        target instanceof HTMLElement &&
        (target.isContentEditable ||
            target.matches('input, textarea, select, [role="textbox"]'))
    );
}

const shortcutModifier = /Mac|iPhone|iPad/i.test(navigator.platform)
    ? '⌘'
    : 'Ctrl';


export function CommandPalette({
    locale,
    profile,
    onNavigate,
    onLocaleChange,
    onProfileChange,
    onPortfolioChanged,
    googleStatus,
    onSchedulesChanged,
    onExportAllReports,
    onReportCreate,
    onReportOpen,
    onReportsChanged,
    onCustomReportSave,
    onNotify,
}: CommandPaletteProps) {
    const [isOpen, setIsOpen] = useState(false);
    const [activeDialog, setActiveDialog] = useState<PaletteDialog | null>(
        null,
    );
    const [query, setQuery] = useState('');
    const [activeIndex, setActiveIndex] = useState(0);
    const inputRef = useRef<HTMLInputElement>(null);
    const paletteRef = useRef<HTMLDivElement>(null);
    const rowRefs = useRef(new Map<string, HTMLButtonElement>());
    const returnFocusRef = useRef<HTMLElement | null>(null);
    const restoreFocusOnClose = useRef(true);
    const t = (key: string) => translate(locale, key);

    const closePalette = useCallback((restoreFocus = true) => {
        restoreFocusOnClose.current = restoreFocus;
        setIsOpen(false);
        setQuery('');
        setActiveIndex(0);
    }, []);

    const openDialog = useCallback(
        (dialog: PaletteDialog) => {
            if (!isOpen) {
                returnFocusRef.current =
                    document.activeElement instanceof HTMLElement
                        ? document.activeElement
                        : null;
            }
            if (dialog === 'createReport') {
                returnFocusRef.current?.focus();
            }
            restoreFocusOnClose.current = false;
            setIsOpen(false);
            setQuery('');
            setActiveIndex(0);
            setActiveDialog(dialog);
        },
        [isOpen],
    );

    const navigate = useCallback(
        (view: DashboardView) => {
            closePalette(false);
            onNavigate(view);
            window.requestAnimationFrame(() => {
                document.getElementById('main-content')?.focus();
            });
        },
        [closePalette, onNavigate],
    );

    /* hardcoded commands */
    const commands = useMemo<CommandOption<PaletteCommandData>[]>(
        () => [
            {
                id: 'create-report',
                label: t('command.createReport'),
                keywords: [
                    'report',
                    'analysis',
                    'new',
                    'generate',
                    'reporte',
                    'analisis',
                    'crear',
                    'generar',
                    'rapport',
                    'analyse',
                    'nouveau',
                    'generer',
                ],
                group: t('command.group.quickActions'),
                data: {
                    description: t('command.createReportDescription'),
                    icon: FileText,
                    shortcut: [shortcutModifier, 'Alt', 'R'],
                    execute: () => openDialog('createReport'),
                },
            },
            {
                id: 'configure-api-keys',
                label: t('command.configureApiKeys'),
                keywords: [
                    'api',
                    'key',
                    'keys',
                    'provider',
                    'openai',
                    'anthropic',
                    'deepseek',
                    'clave',
                    'claves',
                    'clé',
                    'clés',
                    'fournisseur',
                ],
                group: t('command.group.quickActions'),
                data: {
                    description: t('command.configureApiKeysDescription'),
                    icon: KeyRound,
                    shortcut: [shortcutModifier, 'Alt', 'K'],
                    execute: () => openDialog('apiKeys'),
                },
            },
            {
                id: 'add-watchlist-ticker',
                label: t('command.addWatchlist'),
                keywords: [
                    'ticker',
                    'stock',
                    'symbol',
                    'asset',
                    'watchlist',
                    'activo',
                    'accion',
                    'simbolo',
                    'añadir',
                    'agregar',
                    'actif',
                    'suivi',
                    'surveillance',
                    'ajouter',
                ],
                group: t('command.group.quickActions'),
                data: {
                    description: t('command.addWatchlistDescription'),
                    icon: Plus,
                    shortcut: [shortcutModifier, 'Alt', 'W'],
                    execute: () => openDialog('watchlist'),
                },
            },
            {
                id: 'change-language',
                label: t('command.changeLanguage'),
                keywords: [
                    'language',
                    'locale',
                    'english',
                    'spanish',
                    'idioma',
                    'español',
                    'ingles',
                    'french',
                    'français',
                    'francais',
                    'langue',
                ],
                group: t('command.group.quickActions'),
                data: {
                    description: t('command.changeLanguageDescription'),
                    icon: Languages,
                    shortcut: [shortcutModifier, 'Alt', 'L'],
                    execute: () => openDialog('language'),
                },
            },
            {
                id: 'add-portfolio-trade',
                label: t('command.addPortfolioTrade'),
                keywords: [
                    'buy',
                    'sell',
                    'trade',
                    'purchase',
                    'portfolio',
                    'operacion',
                    'compra',
                    'venta',
                    'portafolio',
                    'accion',
                    'acheter',
                    'vendre',
                    'opération',
                    'portefeuille',
                ],
                group: t('command.group.quickActions'),
                data: {
                    description: t('command.addPortfolioTradeDescription'),
                    icon: BriefcaseBusiness,
                    shortcut: [shortcutModifier, 'Alt', 'P'],
                    execute: () => openDialog('portfolioTrade'),
                },
            },
            {
                id: 'export-all-reports',
                label: t('command.exportAllReports'),
                keywords: [
                    'download',
                    'export',
                    'all reports',
                    'descargar',
                    'todos',
                    'reportes',
                    'exportar',
                    'télécharger',
                    'exporter',
                    'rapports',
                ],
                group: t('command.group.quickActions'),
                data: {
                    description: t('command.exportAllReportsDescription'),
                    icon: Download,
                    shortcut: [shortcutModifier, 'Alt', 'D'],
                    execute: () => {
                        closePalette(false);
                        void onExportAllReports();
                    },
                },
            },
            {
                id: 'connect-google',
                label: t(
                    googleStatus?.connected
                        ? 'command.manageGoogle'
                        : 'command.connectGoogle',
                ),
                keywords: [
                    'google',
                    'gmail',
                    'oauth',
                    'connect',
                    'email',
                    'conectar',
                    'correo',
                    'connecter',
                    'courriel',
                ],
                group: t('command.group.quickActions'),
                data: {
                    description: t('command.connectGoogleDescription'),
                    icon: Mail,
                    shortcut: [shortcutModifier, 'Alt', 'G'],
                    execute: () => openDialog('google'),
                },
            },
            {
                id: 'install-ollama',
                label: t('command.installOllama'),
                keywords: [
                    'download',
                    'install',
                    'local ai',
                    'ollama',
                    'descargar',
                    'instalar',
                    'ia local',
                    'télécharger',
                    'installer',
                    'ia locale',
                ],
                group: t('command.group.quickActions'),
                data: {
                    description: t('command.installOllamaDescription'),
                    icon: Download,
                    shortcut: [shortcutModifier, 'Alt', 'I'],
                    execute: () => openDialog('installOllama'),
                },
            },
            {
                id: 'start-ollama',
                label: t('command.startOllama'),
                keywords: [
                    'start',
                    'service',
                    'local model',
                    'ollama',
                    'iniciar',
                    'servicio',
                    'modelo local',
                    'démarrer',
                    'démarrer ollama',
                    'modèle local',
                ],
                group: t('command.group.quickActions'),
                data: {
                    description: t('command.startOllamaDescription'),
                    icon: Cpu,
                    shortcut: [shortcutModifier, 'Alt', 'O'],
                    execute: () => openDialog('startOllama'),
                },
            },
            {
                id: 'open-reports',
                label: t('command.openReports'),
                keywords: [
                    'home',
                    'library',
                    'overview',
                    'reportes',
                    'inicio',
                    'rapport',
                    'bibliothèque',
                    'aperçu',
                ],
                group: t('command.group.navigation'),
                data: {
                    description: t('command.openReportsDescription'),
                    icon: BarChart3,
                    execute: () => navigate('overview'),
                },
            },
            {
                id: 'open-watchlist',
                label: t('command.openWatchlist'),
                keywords: [
                    'track',
                    'assets',
                    'watchlist',
                    'seguimiento',
                    'suivi',
                    'actifs',
                    'liste de suivi',
                ],
                group: t('command.group.navigation'),
                data: {
                    description: t('command.openWatchlistDescription'),
                    icon: LineChart,
                    execute: () => navigate('watchlist'),
                },
            },
            {
                id: 'open-portfolio',
                label: t('command.openPortfolio'),
                keywords: [
                    'holdings',
                    'trades',
                    'portafolio',
                    'tenencias',
                    'positions',
                    'opérations',
                    'portefeuille',
                ],
                group: t('command.group.navigation'),
                data: {
                    description: t('command.openPortfolioDescription'),
                    icon: BriefcaseBusiness,
                    execute: () => navigate('portfolio'),
                },
            },
            {
                id: 'open-schedules',
                label: t('command.openSchedules'),
                keywords: [
                    'schedule',
                    'scheduled',
                    'email',
                    'programacion',
                    'programado',
                    'correo',
                    'planification',
                    'planifié',
                    'courriel',
                ],
                group: t('command.group.navigation'),
                data: {
                    description: t('command.openSchedulesDescription'),
                    icon: CalendarClock,
                    execute: () => navigate('schedules'),
                },
            },
            {
                id: 'open-settings',
                label: t('command.openSettings'),
                keywords: [
                    'preferences',
                    'settings',
                    'preferencias',
                    'ajustes',
                    'préférences',
                    'paramètres',
                ],
                group: t('command.group.navigation'),
                data: {
                    description: t('command.openSettingsDescription'),
                    icon: Settings2,
                    execute: () => navigate('settings'),
                },
            },
            {
                id: 'open-ai-providers',
                label: t('command.openAiProviders'),
                keywords: [
                    'ollama',
                    'models',
                    'ai',
                    'ia',
                    'modelos',
                    'modèles',
                ],
                group: t('command.group.navigation'),
                data: {
                    description: t('command.openAiProvidersDescription'),
                    icon: BrainCircuit,
                    execute: () => navigate('aiProviders'),
                },
            },
        ],
        [
            googleStatus?.connected,
            locale,
            navigate,
            onExportAllReports,
            openDialog,
            shortcutModifier,
        ],
    );

    const filteredCommands = useMemo(
        () => fuzzyFilter(commands, query.trim()),
        [commands, query],
    );
    const selectedCommand = filteredCommands[activeIndex];
    const groupedCommands = useMemo(() => {
        const groups: Array<{
            label: string;
            options: CommandOption<PaletteCommandData>[];
        }> = [];
        for (const option of filteredCommands) {
            const label = option.group ?? '';
            let group = groups.find((item) => item.label === label);
            if (!group) {
                group = { label, options: [] };
                groups.push(group);
            }
            group.options.push(option);
        }
        return groups;
    }, [filteredCommands]);

    useEffect(() => {
        setActiveIndex(0);
    }, [query, locale]);

    useEffect(() => {
        if (activeIndex >= filteredCommands.length) {
            setActiveIndex(Math.max(0, filteredCommands.length - 1));
        }
    }, [activeIndex, filteredCommands.length]);

    useEffect(() => {
        const activeId = selectedCommand?.id;
        if (activeId) {
            rowRefs.current.get(activeId)?.scrollIntoView({
                block: 'nearest',
            });
        }
    }, [selectedCommand?.id]);

    useEffect(() => {
        const handleGlobalKeyDown = (event: KeyboardEvent) => {
            const activeModal =
                document.querySelector<HTMLElement>('[aria-modal="true"]');
            if (
                event.key === 'F4' &&
                !event.altKey &&
                !event.ctrlKey &&
                !event.metaKey &&
                !event.shiftKey
            ) {
                if (
                    activeDialog ||
                    (activeModal &&
                        !activeModal.hasAttribute('data-command-palette'))
                ) {
                    return;
                }
                event.preventDefault();
                if (isOpen) {
                    closePalette();
                } else {
                    returnFocusRef.current =
                        document.activeElement instanceof HTMLElement
                            ? document.activeElement
                            : null;
                    restoreFocusOnClose.current = true;
                    setQuery('');
                    setActiveIndex(0);
                    setIsOpen(true);
                }
                return;
            }

            if (
                isOpen ||
                activeDialog ||
                activeModal ||
                isEditableTarget(event.target) ||
                !(event.ctrlKey || event.metaKey) ||
                !event.altKey ||
                event.shiftKey
            ) {
                return;
            }

            const dialogByShortcut: Record<string, PaletteDialog> = {
                r: 'createReport',
                k: 'apiKeys',
                w: 'watchlist',
                l: 'language',
                p: 'portfolioTrade',
                g: 'google',
                i: 'installOllama',
                o: 'startOllama',
            };
            if (event.key.toLowerCase() === 'd') {
                event.preventDefault();
                void onExportAllReports();
                return;
            }
            const dialog = dialogByShortcut[event.key.toLowerCase()];
            if (dialog) {
                event.preventDefault();
                openDialog(dialog);
            }
        };

        document.addEventListener('keydown', handleGlobalKeyDown);
        return () =>
            document.removeEventListener('keydown', handleGlobalKeyDown);
    }, [
        activeDialog,
        closePalette,
        isOpen,
        onExportAllReports,
        openDialog,
    ]);

    useEffect(() => {
        if (!isOpen) {
            return;
        }

        const focusFrame = window.requestAnimationFrame(() =>
            inputRef.current?.focus(),
        );
        const trapTab = (event: KeyboardEvent) => {
            if (event.key !== 'Tab' || !paletteRef.current) {
                return;
            }
            const focusable = Array.from(
                paletteRef.current.querySelectorAll<HTMLElement>(
                    'input:not([disabled]), button:not([disabled])',
                ),
            );
            const first = focusable[0];
            const last = focusable[focusable.length - 1];
            if (!first || !last) {
                event.preventDefault();
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
        document.addEventListener('keydown', trapTab);
        return () => {
            window.cancelAnimationFrame(focusFrame);
            document.removeEventListener('keydown', trapTab);
            if (
                restoreFocusOnClose.current &&
                !document.querySelector(
                    '[aria-modal="true"]:not([data-command-palette])',
                )
            ) {
                returnFocusRef.current?.focus();
            }
        };
    }, [isOpen]);

    function executeCommand(option: CommandOption<PaletteCommandData>) {
        option.data?.execute();
    }

    function handlePaletteKeyDown(
        event: ReactKeyboardEvent<HTMLDivElement>,
    ) {
        if (event.key === 'ArrowDown') {
            if (filteredCommands.length === 0) {
                return;
            }
            event.preventDefault();
            setActiveIndex((index) =>
                Math.min(index + 1, filteredCommands.length - 1),
            );
        } else if (event.key === 'ArrowUp') {
            if (filteredCommands.length === 0) {
                return;
            }
            event.preventDefault();
            setActiveIndex((index) => Math.max(index - 1, 0));
        } else if (event.key === 'Home' && filteredCommands.length > 0) {
            event.preventDefault();
            setActiveIndex(0);
        } else if (
            event.key === 'End' &&
            filteredCommands.length > 0
        ) {
            event.preventDefault();
            setActiveIndex(filteredCommands.length - 1);
        } else if (event.key === 'Enter' && selectedCommand) {
            event.preventDefault();
            executeCommand(selectedCommand);
        } else if (event.key === 'Escape') {
            event.preventDefault();
            closePalette();
        }
    }

    return (
        <>
            {createPortal(
                <AnimatePresence initial={false}>
                    {isOpen && (
                        <motion.div
                            animate={{ opacity: 1 }}
                            aria-label={t('command.paletteTitle')}
                            aria-modal='true'
                            className='command-palette-backdrop'
                            data-command-palette=''
                            exit={{ opacity: 0 }}
                            initial={{ opacity: 0 }}
                            key='command-palette'
                            onMouseDown={(event) => {
                                if (event.target === event.currentTarget) {
                                    closePalette();
                                }
                            }}
                            onKeyDown={handlePaletteKeyDown}
                            role='dialog'
                            transition={{ duration: 0.14, ease: 'easeOut' }}
                        >
                            <motion.div
                                animate={{ opacity: 1, scale: 1, y: 0 }}
                                className='command-palette'
                                exit={{ opacity: 0, scale: 0.98, y: -8 }}
                                initial={{ opacity: 0, scale: 0.98, y: -8 }}
                                ref={paletteRef}
                                transition={{
                                    type: 'spring',
                                    stiffness: 420,
                                    damping: 32,
                                }}
                            >
                                <div className='command-palette-search'>
                                    <Search
                                        size={17}
                                        aria-hidden='true'
                                    />
                                    <input
                                        aria-activedescendant={
                                            selectedCommand?.id
                                                ? `command-option-${selectedCommand.id}`
                                                : undefined
                                        }
                                        aria-autocomplete='list'
                                        aria-controls='command-palette-list'
                                        aria-expanded='true'
                                        aria-label={t(
                                            'command.paletteTitle',
                                        )}
                                        autoComplete='off'
                                        onChange={(event) =>
                                            setQuery(event.target.value)
                                        }
                                        placeholder={t(
                                            'command.searchPlaceholder',
                                        )}
                                        ref={inputRef}
                                        role='combobox'
                                        value={query}
                                    />
                                    <kbd className='command-search-hint'>
                                        Esc
                                    </kbd>
                                </div>

                                <div
                                    className='command-palette-list'
                                    id='command-palette-list'
                                    role='listbox'
                                    aria-label={t('command.paletteTitle')}
                                >
                                    {groupedCommands.length > 0 ? (
                                        groupedCommands.map((group, index) => (
                                            <div
                                                aria-labelledby={`command-group-${index}`}
                                                className='command-palette-group'
                                                key={group.label}
                                                role='group'
                                            >
                                                <p
                                                    className='command-group-label'
                                                    id={`command-group-${index}`}
                                                >
                                                    {group.label}
                                                </p>
                                                <div className='command-group-items'>
                                                    <AnimatePresence
                                                        initial={false}
                                                        mode='popLayout'
                                                    >
                                                        {group.options.map(
                                                            (option) => {
                                                                const id =
                                                                    option.id ??
                                                                    option.label;
                                                                const index =
                                                                    filteredCommands.findIndex(
                                                                        (
                                                                            item,
                                                                        ) =>
                                                                            item.id ===
                                                                            option.id,
                                                                    );
                                                                const isSelected =
                                                                    index ===
                                                                    activeIndex;
                                                                const data =
                                                                    option.data;
                                                                if (!data) {
                                                                    return null;
                                                                }
                                                                const Icon =
                                                                    data.icon;
                                                                return (
                                                                    <motion.button
                                                                        animate={{
                                                                            opacity: 1,
                                                                            y: 0,
                                                                        }}
                                                                        aria-selected={
                                                                            isSelected
                                                                        }
                                                                        className='command-palette-item'
                                                                        exit={{
                                                                            opacity: 0,
                                                                            y: -4,
                                                                        }}
                                                                        initial={{
                                                                            opacity: 0,
                                                                            y: 4,
                                                                        }}
                                                                        key={id}
                                                                        layout
                                                                        onClick={() =>
                                                                            executeCommand(
                                                                                option,
                                                                            )
                                                                        }
                                                                        onMouseEnter={() =>
                                                                            setActiveIndex(
                                                                                index,
                                                                            )
                                                                        }
                                                                        onFocus={() =>
                                                                            setActiveIndex(
                                                                                index,
                                                                            )
                                                                        }
                                                                        ref={(
                                                                            element,
                                                                        ) => {
                                                                            if (
                                                                                element
                                                                            ) {
                                                                                rowRefs.current.set(
                                                                                    id,
                                                                                    element,
                                                                                );
                                                                            } else {
                                                                                rowRefs.current.delete(
                                                                                    id,
                                                                                );
                                                                            }
                                                                        }}
                                                                        role='option'
                                                                        tabIndex={
                                                                            0
                                                                        }
                                                                        type='button'
                                                                        transition={{
                                                                            duration: 0.13,
                                                                            ease: 'easeOut',
                                                                        }}
                                                                        whileTap={{
                                                                            scale: 0.995,
                                                                        }}
                                                                    >
                                                                        <span className='command-item-icon'>
                                                                            <Icon
                                                                                size={
                                                                                    16
                                                                                }
                                                                                aria-hidden='true'
                                                                            />
                                                                        </span>
                                                                        <span className='command-item-copy'>
                                                                            <span className='command-item-label'>
                                                                                {
                                                                                    option.label
                                                                                }
                                                                            </span>
                                                                            <span className='command-item-description'>
                                                                                {
                                                                                    data.description
                                                                                }
                                                                            </span>
                                                                        </span>
                                                                        {data.shortcut && (
                                                                            <span
                                                                                aria-label={data.shortcut.join(
                                                                                    ' + ',
                                                                                )}
                                                                                className='command-shortcut'
                                                                            >
                                                                                {data.shortcut.map(
                                                                                    (
                                                                                        key,
                                                                                    ) => (
                                                                                        <kbd
                                                                                            key={
                                                                                                key
                                                                                            }
                                                                                        >
                                                                                            {
                                                                                                key
                                                                                            }
                                                                                        </kbd>
                                                                                    ),
                                                                                )}
                                                                            </span>
                                                                        )}
                                                                    </motion.button>
                                                                );
                                                            },
                                                        )}
                                                    </AnimatePresence>
                                                </div>
                                            </div>
                                        ))
                                    ) : (
                                        <div
                                            className='command-empty-state'
                                            role='status'
                                        >
                                            {t('command.noResults')}
                                        </div>
                                    )}
                                </div>

                                <footer className='command-palette-footer'>
                                    <span>
                                        <kbd>↑</kbd>
                                        <kbd>↓</kbd>
                                        {t('command.keyboard.navigate')}
                                    </span>
                                    <span>
                                        <kbd>↵</kbd>
                                        {t('command.keyboard.select')}
                                    </span>
                                    <span>
                                        <kbd>Esc</kbd>
                                        {t('command.keyboard.close')}
                                    </span>
                                    <span className='command-footer-open'>
                                        <kbd>F4</kbd>
                                        {t('command.keyboard.open')}
                                    </span>
                                </footer>
                            </motion.div>
                        </motion.div>
                    )}
                </AnimatePresence>,
                document.body,
            )}

            <CreateReportCommand
                isOpen={activeDialog === 'createReport'}
                locale={locale}
                onClose={() => setActiveDialog(null)}
                onCreate={onReportCreate}
                onOpen={onReportOpen}
                onReportsChanged={onReportsChanged}
                onSaveCustomReport={onCustomReportSave}
                profile={profile}
            />
            <ConfigureApiKeys
                isOpen={activeDialog === 'apiKeys'}
                locale={locale}
                onClose={() => setActiveDialog(null)}
                returnFocusTarget={returnFocusRef.current}
            />
            <AddWatchlistTicker
                isOpen={activeDialog === 'watchlist'}
                locale={locale}
                onClose={() => setActiveDialog(null)}
                onNotify={onNotify}
                onProfileChange={onProfileChange}
                profile={profile}
                returnFocusTarget={returnFocusRef.current}
            />
            <ChangeLanguage
                isOpen={activeDialog === 'language'}
                locale={locale}
                onChangeLocale={onLocaleChange}
                onClose={() => setActiveDialog(null)}
                onNotify={onNotify}
                returnFocusTarget={returnFocusRef.current}
            />
            <AddPortfolioTrade
                isOpen={activeDialog === 'portfolioTrade'}
                locale={locale}
                onClose={() => setActiveDialog(null)}
                onNotify={onNotify}
                onPortfolioChanged={onPortfolioChanged}
                returnFocusTarget={returnFocusRef.current}
            />
            <ConnectGoogle
                googleStatus={googleStatus}
                isOpen={activeDialog === 'google'}
                locale={locale}
                onClose={() => setActiveDialog(null)}
                onNotify={onNotify}
                onRefresh={onSchedulesChanged}
                returnFocusTarget={returnFocusRef.current}
            />
            <OllamaAction
                isOpen={activeDialog === 'installOllama'}
                locale={locale}
                onClose={() => setActiveDialog(null)}
                onNotify={onNotify}
                operation='install'
                returnFocusTarget={returnFocusRef.current}
            />
            <OllamaAction
                isOpen={activeDialog === 'startOllama'}
                locale={locale}
                onClose={() => setActiveDialog(null)}
                onNotify={onNotify}
                operation='start'
                returnFocusTarget={returnFocusRef.current}
            />
        </>
    );
}
