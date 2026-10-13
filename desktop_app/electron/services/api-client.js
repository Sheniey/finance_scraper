class ApiRequestError extends Error {
    constructor(message, status, code) {
        super(message);
        this.name = 'ApiRequestError';
        this.status = status;
        this.code = code;
    }
}

async function parseResponse(response) {
    const content = await response.text();
    if (!content) {
        return null;
    }
    try {
        return JSON.parse(content);
    } catch (error) {
        throw new Error(
            `The local API returned invalid JSON (HTTP ${response.status}).`,
            { cause: error },
        );
    }
}

function delay(milliseconds) {
    return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

export class FinanceApiClient {
    constructor(apiManager) {
        this.api = apiManager;
        this.session = null;
    }

    getProfile() {
        return this.session?.profile ?? null;
    }

    async #requestRaw(
        endpoint,
        { method = 'GET', body, auth = false, internal = false } = {},
    ) {
        const headers = {};
        if (auth) {
            if (!this.session?.accessToken) {
                throw new ApiRequestError(
                    'Sign in to Finance Scraper to continue.',
                    401,
                    'SESSION_REQUIRED',
                );
            }
            headers.Authorization = `Bearer ${this.session.accessToken}`;
        }
        const response = await this.api.request(endpoint, {
            method,
            body,
            headers,
            internal,
        });
        const payload = await parseResponse(response);
        if (!response.ok) {
            throw new ApiRequestError(
                payload?.message || `The local API returned HTTP ${response.status}.`,
                response.status,
                payload?.error || 'API_REQUEST_FAILED',
            );
        }
        return payload;
    }

    async #refreshSession() {
        if (!this.session?.refreshToken) {
            this.session = null;
            throw new ApiRequestError(
                'Your Finance Scraper session has expired. Sign in again.',
                401,
                'SESSION_EXPIRED',
            );
        }
        try {
            const pair = await this.#requestRaw('/auth/refresh', {
                method: 'POST',
                body: { refresh_token: this.session.refreshToken },
            });
            this.session = {
                ...this.session,
                accessToken: pair.access_token,
                refreshToken: pair.refresh_token,
                expiresAt: Date.now() + pair.expires_in * 1_000,
            };
        } catch (error) {
            this.session = null;
            throw error;
        }
    }

    async #ensureFreshAccessToken() {
        if (!this.session) {
            throw new ApiRequestError(
                'Sign in to Finance Scraper to continue.',
                401,
                'SESSION_REQUIRED',
            );
        }
        if (this.session.expiresAt - Date.now() < 30_000) {
            await this.#refreshSession();
        }
    }

    async request(endpoint, options = {}) {
        if (!options.auth) {
            return this.#requestRaw(endpoint, options);
        }
        await this.#ensureFreshAccessToken();
        try {
            return await this.#requestRaw(endpoint, options);
        } catch (error) {
            if (!(error instanceof ApiRequestError) || error.status !== 401) {
                throw error;
            }
            await this.#refreshSession();
            return this.#requestRaw(endpoint, options);
        }
    }

    async login(credentials) {
        const pair = await this.request('/auth/login', {
            method: 'POST',
            body: credentials,
        });
        return this.#completeSession(pair);
    }

    async startGoogleLogin() {
        return this.request('/auth/google/authorize', {
            method: 'POST',
            internal: true,
        });
    }

    async getGoogleLoginFlow(flowId) {
        return this.request(
            `/auth/google/flow/${encodeURIComponent(flowId)}`,
            { internal: true },
        );
    }

    async waitForGoogleLogin(flowId) {
        const deadline = Date.now() + 10 * 60 * 1_000;
        while (Date.now() < deadline) {
            const flow = await this.getGoogleLoginFlow(flowId);
            if (flow.status === 'completed') {
                return this.loginWithGoogle(flowId);
            }
            if (flow.status === 'failed') {
                throw new ApiRequestError(
                    'Google sign-in could not be completed. Try again.',
                    400,
                    'GOOGLE_SIGNIN_FAILED',
                );
            }
            await delay(750);
        }
        throw new ApiRequestError(
            'Google sign-in timed out. Try again.',
            408,
            'GOOGLE_SIGNIN_TIMEOUT',
        );
    }

    async loginWithGoogle(flowId) {
        const pair = await this.request('/auth/google/login', {
            method: 'POST',
            body: { flow_id: flowId },
            internal: true,
        });
        return this.#completeSession(pair);
    }

    async #completeSession(pair) {
        this.session = {
            accessToken: pair.access_token,
            refreshToken: pair.refresh_token,
            expiresAt: Date.now() + pair.expires_in * 1_000,
            profile: null,
        };
        try {
            const profile = await this.request('/accounts/me', { auth: true });
            this.session.profile = profile;
            return profile;
        } catch (error) {
            this.session = null;
            throw error;
        }
    }

    async register({ name, email, password, language }) {
        return this.request(
            '/auth/register',
            {
                method: 'POST',
                body: {
                    name,
                    email,
                    password,
                    language: {
                        code: language,
                        name: language === 'en' ? 'English' : 'Español',
                        style: 'friendly',
                    },
                },
                internal: true,
            },
        );
    }

    async logout() {
        if (!this.session) {
            return;
        }
        try {
            await this.request('/auth/logout', {
                method: 'POST',
                auth: true,
            });
        } finally {
            this.session = null;
        }
    }

    async updateProfile(profile) {
        const updated = await this.request('/accounts/me', {
            method: 'PUT',
            auth: true,
            body: {
                name: profile.name,
                email: profile.email,
                language: profile.language,
                custom_report: profile.custom_report,
                watchlist: profile.watchlist,
            },
        });
        if (this.session) {
            this.session.profile = updated;
        }
        return updated;
    }

    listReports(cursor = null) {
        const query = new URLSearchParams({ page_size: '30' });
        if (cursor) {
            query.set('page_cursor', cursor);
        } else {
            query.set('page', '1');
            query.set('sort', '-created_at');
        }
        return this.request(`/reports/me?${query.toString()}`, { auth: true });
    }

    createReport(request) {
        return this.request('/reports/me', {
            method: 'POST',
            auth: true,
            body: request,
        });
    }

    getReport(reportId) {
        return this.request(
            `/reports/${encodeURIComponent(reportId)}`,
            { auth: true },
        );
    }

    async downloadReport(reportId) {
        if (!/^[A-Za-z0-9_-]{1,64}$/.test(reportId)) {
            throw new Error('Report ID has an invalid format.');
        }
        await this.#ensureFreshAccessToken();
        const response = await this.api.request(
            `/reports/${encodeURIComponent(reportId)}/download`,
            {
                headers: {
                    Authorization: `Bearer ${this.session.accessToken}`,
                },
            },
        );
        if (!response.ok) {
            const payload = await parseResponse(response);
            throw new ApiRequestError(
                payload?.message || `The report download failed (HTTP ${response.status}).`,
                response.status,
                payload?.error || 'REPORT_DOWNLOAD_FAILED',
            );
        }
        return {
            content: Buffer.from(await response.arrayBuffer()),
            filename: response.headers.get('content-disposition') ?? '',
            contentType: response.headers.get('content-type') ?? 'application/octet-stream',
        };
    }

    deleteReport(reportId) {
        return this.request(
            `/reports/${encodeURIComponent(reportId)}`,
            { method: 'DELETE', auth: true },
        );
    }

    getGoogleStatus() {
        return this.request('/integrations/google/status', { auth: true });
    }

    async connectGoogle() {
        const result = await this.request(
            '/integrations/google/authorize',
            { method: 'POST', auth: true },
        );
        return result;
    }

    getGoogleFlow(flowId) {
        return this.request(
            `/integrations/google/callback/${encodeURIComponent(flowId)}`,
            { auth: true },
        );
    }

    disconnectGoogle() {
        return this.request(
            '/integrations/google/status',
            { method: 'DELETE', auth: true },
        );
    }

    listSchedules() {
        return this.request('/schedules/me', { auth: true });
    }

    createSchedule(request) {
        return this.request('/schedules/me', {
            method: 'POST',
            auth: true,
            body: request,
        });
    }

    setScheduleEnabled(scheduleId, enabled) {
        return this.request(
            `/schedules/me/${encodeURIComponent(scheduleId)}`,
            {
                method: 'PATCH',
                auth: true,
                body: { enabled },
            },
        );
    }

    deleteSchedule(scheduleId) {
        return this.request(
            `/schedules/me/${encodeURIComponent(scheduleId)}`,
            { method: 'DELETE', auth: true },
        );
    }
}

export { ApiRequestError };
