
import type { SupportedLocale } from './locales.js';

export type Locale = SupportedLocale;
export type AiProviderName = 'openai' | 'deepseek' | 'anthropic';
export type ReportFormat = 'pdf' | 'json' | 'yaml' | 'toml' | 'llm' | 'txt' | 'xlsx';
export type ReportStatus = 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'FAILED';
export type DashboardView =
    | 'overview'
    | 'watchlist'
    | 'portfolio'
    | 'schedules'
    | 'settings'
    | 'aiProviders';

export interface WatchlistItem {
    ticker: string;
    region: string;
    mode: string;
    llm_explanation: boolean;
    charts: boolean;
    horizon: number;
    enabled: boolean;
}

export interface UserProfile {
    id: string;
    name: string;
    email: string;
    role: string;
    language: {
        code: string;
        name: string;
        style: string;
    };
    custom_report: string[];
    watchlist: Array<WatchlistItem | null>;
}

export interface ReportEntry {
    report_id: string;
    status: ReportStatus;
    ticker: string;
    filename: string;
    report_format: ReportFormat;
    created_at: string;
    updated_at: string;
    started_at: string | null;
    completed_at: string | null;
    expires_at: string | null;
    error_code: string | null;
    download_url: string | null;
}

export interface ReportPage {
    items: ReportEntry[];
    pagination: {
        page: number | null;
        page_size: number;
        total: number;
        has_more: boolean;
        next_cursor: string | null;
    };
}

export interface PortfolioAction {
    action: 'BUY' | 'SELL';
    price: number;
    quantity: number;
    date: string;
}

export interface PortfolioHolding {
    ticker: string;
    region: string;
    currency: string;
    actions: PortfolioAction[];
}

export interface PortfolioResponse {
    portfolio: PortfolioHolding[];
}

export interface CreatePortfolioTradeRequest {
    action: 'BUY' | 'SELL';
    ticker: string;
    region: string;
    currency: string;
    price: number;
    quantity: number;
    date: string;
}

export interface GoogleAccountStatus {
    connected: boolean;
    email: string | null;
    scopes: string[];
}

export interface GoogleOAuthFlow {
    flow_id: string;
    status: 'pending' | 'completed' | 'failed';
    email: string | null;
    error: string | null;
}

export type AiProviderStatus = Record<AiProviderName, boolean>;
export interface OllamaStatus {
    installed: boolean;
    running: boolean;
    models: string[];
    platform: string;
}

export type AiProviderKeyUpdates = Partial<
    Record<AiProviderName, string | null>
>;

export interface ReportSchedule {
    schedule_id: string;
    tickers: string[];
    report_format: ReportFormat;
    run_at: string;
    timezone: string;
    explain: boolean;
    mode: string;
    charts: boolean;
    ml_horizon: number;
    enabled: boolean;
    last_run_date: string | null;
    last_run_status: string | null;
    last_error: string | null;
}

export interface AppSettings {
    locale: Locale;
    reportRetentionSeconds: number;
    workerMaxConcurrency: number;
    financeScraperExecutable: string;
}

export interface ApiStatus {
    state: 'starting' | 'online' | 'stopping' | 'stopped';
    baseUrl: string | null;
    workerConcurrency: number | null;
}

export interface DesktopBootstrap {
    api: ApiStatus;
    settings: AppSettings;
    profile: UserProfile | null;
    workerConcurrency: number | null;
    error: string | null;
}

export interface CreateReportRequest {
    ticker: string;
    filename: string;
    explain: boolean;
    mode: string;
    charts: boolean;
    ml_horizon: number;
}

export interface CreateScheduleRequest {
    tickers: string[];
    report_format: ReportFormat;
    run_at: string;
    timezone: string;
    explain: boolean;
    mode: string;
    charts: boolean;
    ml_horizon: number;
}

export interface DesktopBridge {
    platform: string;
    bootstrap(): Promise<DesktopBootstrap>;
    retryApi(): Promise<ApiStatus>;
    login(credentials: { email: string; password: string }): Promise<UserProfile>;
    register(credentials: {
        name: string;
        email: string;
        password: string;
        language: Locale;
    }): Promise<UserProfile>;
    logout(): Promise<void>;
    updateProfile(profile: UserProfile): Promise<UserProfile>;
    listReports(cursor?: string | null): Promise<ReportPage>;
    createReport(request: CreateReportRequest): Promise<ReportEntry>;
    getReport(reportId: string): Promise<ReportEntry>;
    openReport(reportId: string): Promise<{ path: string }>;
    deleteReport(reportId: string): Promise<void>;
    exportReport(reportId: string): Promise<{ path: string } | null>;
    getPortfolio(): Promise<PortfolioResponse>;
    createPortfolioTrade(
        request: CreatePortfolioTradeRequest,
    ): Promise<PortfolioResponse>;
    getGoogleStatus(): Promise<GoogleAccountStatus>;
    connectGoogle(): Promise<{ flow_id: string }>;
    getGoogleFlow(flowId: string): Promise<GoogleOAuthFlow>;
    disconnectGoogle(): Promise<GoogleAccountStatus>;
    listSchedules(): Promise<ReportSchedule[]>;
    createSchedule(request: CreateScheduleRequest): Promise<ReportSchedule>;
    setScheduleEnabled(
        scheduleId: string,
        enabled: boolean,
    ): Promise<ReportSchedule>;
    deleteSchedule(scheduleId: string): Promise<void>;
    saveSettings(settings: Partial<AppSettings>): Promise<DesktopBootstrap>;
    chooseFinanceScraper(): Promise<string | null>;
    getAiProviderStatus(): Promise<AiProviderStatus>;
    saveAiProviderKeys(
        updates: AiProviderKeyUpdates,
    ): Promise<AiProviderStatus>;
    getOllamaStatus(): Promise<OllamaStatus>;
    installOllama(): Promise<OllamaStatus>;
    startOllama(): Promise<OllamaStatus>;
    onApiState(callback: (status: ApiStatus) => void): () => void;
    onNotification(callback: (message: string) => void): () => void;
}
