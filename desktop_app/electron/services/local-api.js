import { app } from 'electron';
import { spawn } from 'node:child_process';
import { access, mkdir, readFile, writeFile } from 'node:fs/promises';
import net from 'node:net';
import path from 'node:path';

import {
    getAiProviderStatus,
    readAiProviderKeys,
    saveAiProviderKeys,
} from './provider-keys.js';

const STARTUP_TIMEOUT_MS = 90_000;
const HEALTH_CHECK_INTERVAL_MS = 500;
const MAX_CAPTURED_OUTPUT = 12_000;

function delay(milliseconds) {
    return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

function appendOutput(existing, chunk) {
    const combined = `${existing}${chunk}`;
    return combined.length > MAX_CAPTURED_OUTPUT
        ? combined.slice(-MAX_CAPTURED_OUTPUT)
        : combined;
}

async function findExecutable(candidates) {
    for (const candidate of candidates) {
        try {
            await access(candidate);
            return path.resolve(candidate);
        } catch (error) {
            if (error.code !== 'ENOENT' && error.code !== 'ENOTDIR') {
                throw error;
            }
        }
    }
    return null;
}

async function reserveLoopbackPort() {
    const server = net.createServer();
    await new Promise((resolve, reject) => {
        server.once('error', reject);
        server.listen(0, '127.0.0.1', resolve);
    });
    const address = server.address();
    if (!address || typeof address === 'string') {
        await new Promise((resolve) => server.close(resolve));
        throw new Error('Could not reserve a loopback API port.');
    }
    await new Promise((resolve, reject) => {
        server.close((error) => (error ? reject(error) : resolve()));
    });
    return address.port;
}

function getApiConfiguration(userData, settings) {
    const dataDirectory = path.join(userData, 'data');
    return {
        api: {
            database_path: path.join(dataDirectory, 'api-state.sqlite3'),
            report_retention_seconds: settings.reportRetentionSeconds,
            report_worker_poll_seconds: 1,
            report_worker_max_concurrency: settings.workerMaxConcurrency,
        },
        security: {
            access_token_expire_minutes: 15,
            refresh_token_expire_days: 30,
            jwt_config: {
                algorithm: 'HS256',
                issuer: 'finance_scraper',
            },
            rate_limits: {
                login_per_minute: 5,
                register_per_minute: 3,
                report_generation_per_minute: 3,
                default_per_minute: 60,
            },
        },
    };
}

export class LocalApiManager {
    constructor({ appInstance, getSettings, getSecrets, onState }) {
        this.app = appInstance;
        this.getSettings = getSettings;
        this.getSecrets = getSecrets;
        this.onState = onState;
        this.child = null;
        this.startPromise = null;
        this.stopPromise = null;
        this.exitPromise = null;
        this.baseUrl = null;
        this.port = null;
        this.executable = null;
        this.baseArguments = [];
        this.workingDirectory = null;
        this.environment = null;
        this.workerConcurrency = null;
        this.serverPid = null;
        this.pidFile = null;
        this.healthTimer = null;
        this.output = '';
        this.state = 'stopped';
    }

    getStatus() {
        return {
            state: this.state,
            baseUrl: this.baseUrl,
            workerConcurrency: this.workerConcurrency,
        };
    }

    async #getWorkingDirectory() {
        if (this.workingDirectory) {
            return this.workingDirectory;
        }
        const command = await this.#resolveCommand(await this.getSettings());
        return command.workingDirectory;
    }

    async getAiProviderStatus() {
        const workingDirectory = await this.#getWorkingDirectory();
        return getAiProviderStatus(workingDirectory);
    }

    async saveAiProviderKeys(updates) {
        const workingDirectory = await this.#getWorkingDirectory();
        const providerStatus = await saveAiProviderKeys(
            workingDirectory,
            updates,
        );
        if (this.state !== 'online') {
            return providerStatus;
        }

        const stopResult = await this.stop();
        if (stopResult.warning) {
            throw new Error(
                `Provider keys were saved, but the local service could not stop cleanly: ${stopResult.warning}`,
            );
        }
        await this.start();
        return providerStatus;
    }

    async #resolveCommand(settings) {
        if (settings.financeScraperExecutable) {
            const executable = path.resolve(settings.financeScraperExecutable);
            try {
                await access(executable);
            } catch (error) {
                throw new Error(
                    `Finance Scraper executable was not found: ${executable}`,
                    { cause: error },
                );
            }
            return {
                executable,
                baseArguments: [],
                workingDirectory: path.dirname(executable),
            };
        }

        const appPath = this.app.getAppPath();
        const repositoryRoot = path.resolve(appPath, '..');
        const financeRoot = path.join(repositoryRoot, 'finance_scraper');
        if (!this.app.isPackaged) {
            const pythonPath = await findExecutable([
                path.join(
                    financeRoot,
                    '.venv',
                    'Scripts',
                    'python.exe',
                ),
            ]);
            if (pythonPath) {
                return {
                    executable: pythonPath,
                    baseArguments: [path.join(financeRoot, 'finance-cli.py')],
                    workingDirectory: financeRoot,
                };
            }
        }

        const candidates = this.app.isPackaged
            ? [
                path.join(
                    process.resourcesPath,
                    'finance-scraper',
                    'finance-scraper.exe',
                ),
                path.join(
                    path.dirname(process.execPath),
                    'finance-scraper',
                    'finance-scraper.exe',
                ),
                path.join(
                    path.dirname(process.execPath),
                    'finance_scraper',
                    'dist',
                    'finance-scraper',
                    'finance-scraper.exe',
                ),
                path.join(
                    repositoryRoot,
                    'finance_scraper',
                    'dist',
                    'finance-scraper',
                    'finance-scraper.exe',
                ),
            ]
            : [
                path.join(
                    financeRoot,
                    'dist',
                    'finance-scraper',
                    'finance-scraper.exe',
                ),
            ];
        const executable = await findExecutable(candidates);
        if (executable) {
            return {
                executable,
                baseArguments: [],
                workingDirectory: path.dirname(executable),
            };
        }
        throw new Error(
            'Finance Scraper executable was not found. Select finance-scraper.exe in Settings.',
        );
    }

    async #buildEnvironment(settings, secrets) {
        const userData = this.app.getPath('userData');
        const dataDirectory = path.join(userData, 'data');
        const providerKeys = await readAiProviderKeys(this.workingDirectory);
        await mkdir(dataDirectory, { recursive: true });
        const apiConfigPath = path.join(userData, 'desktop-api.json');
        await writeFile(
            apiConfigPath,
            `${JSON.stringify(getApiConfiguration(userData, settings), null, 2)}\n`,
            { encoding: 'utf8', mode: 0o600 },
        );

        const environment = {
            ...process.env,
            APP_ENV: 'production',
            API_CONFIG_PATH: apiConfigPath,
            DB_LOCAL_PATH: path.join(dataDirectory, 'accounts.sqlite3'),
            REPORT_STORE_PATH: path.join(dataDirectory, 'reports.sqlite3'),
            DB_LOCATION: '',
            DB_URL: '',
            DB_AUTH_TOKEN: '',
            TURSO_AUTH_TOKEN: '',
            FINANCE_DESKTOP_LOCAL_ONLY: '1',
            FINANCE_API_FOREGROUND: '1',
            FINANCE_DESKTOP_CONTROL_TOKEN: secrets.controlToken,
            GOOGLE_OAUTH_CLIENT_ID: settings.googleClientId,
            JWT_SECRET_KEY: secrets.jwtSecretKey,
            OPENAI_API_KEY: providerKeys.openai ?? '',
            CHATGPT_API_KEY: providerKeys.openai ?? '',
            DEEPSEEK_API_KEY: providerKeys.deepseek ?? '',
            ANTHROPIC_API_KEY: providerKeys.anthropic ?? '',
        };
        for (const variable of [
            'EMAIL_ADDRESS',
            'EMAIL_PASSWORD',
            'EMAIL_HOST',
            'EMAIL_PORT',
            'EMAIL_USE_TLS',
            'EMAIL_USE_SSL',
            'GMAIL_APP_PASSWORD',
            'GOOGLE_APP_PASSWORD',
        ]) {
            delete environment[variable];
        }
        return environment;
    }

    async start() {
        if (this.state === 'online') {
            return this.getStatus();
        }
        if (this.startPromise) {
            return this.startPromise;
        }
        if (this.child || this.pidFile) {
            await this.stop();
        }
        this.startPromise = this.#start();
        try {
            return await this.startPromise;
        } finally {
            this.startPromise = null;
        }
    }

    async #start() {
        const settings = await this.getSettings();
        const secrets = await this.getSecrets();
        const command = await this.#resolveCommand(settings);
        this.executable = command.executable;
        this.baseArguments = command.baseArguments;
        this.workingDirectory = command.workingDirectory;
        this.environment = await this.#buildEnvironment(settings, secrets);
        this.port = await reserveLoopbackPort();
        this.baseUrl = `http://127.0.0.1:${this.port}`;
        this.output = '';
        this.state = 'starting';
        this.onState?.(this.getStatus());

        const pidFile = path.join(
            this.app.getPath('userData'),
            'runtime',
            'api.pid',
        );
        this.pidFile = pidFile;
        await mkdir(path.dirname(pidFile), { recursive: true });
        const args = [
            ...this.baseArguments,
            'api',
            'serve',
            '--foreground',
            '--host',
            '127.0.0.1',
            '--port',
            String(this.port),
            '--pid-file',
            pidFile,
        ];
        console.info(
            'Starting Finance Scraper API with:',
            this.executable,
            ...args,
            'desktop-local-only=',
            this.environment.FINANCE_DESKTOP_LOCAL_ONLY,
        );
        const child = spawn(this.executable, args, {
            cwd: this.workingDirectory,
            env: this.environment,
            stdio: ['ignore', 'pipe', 'pipe'],
            windowsHide: true,
            shell: false,
        });
        this.child = child;
        this.exitPromise = new Promise((resolve) => {
            child.once('error', (error) => {
                this.output = appendOutput(
                    this.output,
                    `${error.message}\n`,
                );
                resolve({ code: null, error });
            });
            child.once('close', (code, signal) => {
                resolve({ code, signal });
            });
        });
        child.stdout.setEncoding('utf8');
        child.stderr.setEncoding('utf8');
        child.stdout.on('data', (chunk) => {
            this.output = appendOutput(this.output, chunk);
        });
        child.stderr.on('data', (chunk) => {
            this.output = appendOutput(this.output, chunk);
        });

        try {
            const deadline = Date.now() + STARTUP_TIMEOUT_MS;
            while (Date.now() < deadline) {
                if (
                    (child.exitCode !== null && child.exitCode !== 0) ||
                    child.signalCode !== null
                ) {
                    throw new Error(
                        `Finance Scraper API stopped during startup.\n${this.output}`,
                    );
                }
                try {
                    const response = await fetch(`${this.baseUrl}/desktop/health`, {
                        headers: {
                            'X-Finance-Desktop-Token': secrets.controlToken,
                        },
                        signal: AbortSignal.timeout(1_000),
                    });
                    if (response.status === 200) {
                        const health = await response.json();
                        let pidText;
                        try {
                            pidText = await readFile(pidFile, 'utf8');
                        } catch (error) {
                            if (error.code === 'ENOENT') {
                                await delay(HEALTH_CHECK_INTERVAL_MS);
                                continue;
                            }
                            throw error;
                        }
                        const apiPid = Number(pidText.trim());
                        if (
                            !Number.isSafeInteger(apiPid) ||
                            health.process_id !== apiPid
                        ) {
                            throw new Error(
                                'The local API process ID did not match its verified PID file.',
                            );
                        }
                        this.serverPid = apiPid;
                        this.workerConcurrency = health.report_worker_max_concurrency;
                        this.state = 'online';
                        this.#startHealthMonitor(secrets.controlToken);
                        this.onState?.(this.getStatus());
                        return this.getStatus();
                    }
                    throw new Error(
                        `The local API health check failed with HTTP ${response.status}.`,
                    );
                } catch (error) {
                    if (
                        error instanceof TypeError ||
                        error.name === 'TimeoutError' ||
                        error.name === 'AbortError'
                    ) {
                        await delay(HEALTH_CHECK_INTERVAL_MS);
                        continue;
                    }
                    throw error;
                }
            }

            throw new Error(
                `Finance Scraper API did not become ready in time.\n${this.output}`,
            );
        } catch (error) {
            try {
                await this.stop();
            } catch (stopError) {
                throw new AggregateError(
                    [error, stopError],
                    'API startup failed and the failed process could not be stopped.',
                );
            }
            throw error;
        }
    }

    #startHealthMonitor(controlToken) {
        if (this.healthTimer) {
            clearInterval(this.healthTimer);
        }
        this.healthTimer = setInterval(() => {
            void this.#checkHealth(controlToken);
        }, 5_000);
        this.healthTimer.unref?.();
    }

    async #checkHealth(controlToken) {
        if (this.state !== 'online' || !this.baseUrl) {
            return;
        }
        try {
            const response = await fetch(`${this.baseUrl}/desktop/health`, {
                headers: {
                    'X-Finance-Desktop-Token': controlToken,
                },
                signal: AbortSignal.timeout(2_000),
            });
            if (!response.ok) {
                throw new Error(
                    `Local API health check failed with HTTP ${response.status}.`,
                );
            }
            const health = await response.json();
            if (health.process_id !== this.serverPid) {
                throw new Error('The local API process identity changed.');
            }
        } catch (error) {
            this.output = appendOutput(this.output, `${error.message}\n`);
            this.#markStopped();
        }
    }

    #markStopped() {
        if (this.healthTimer) {
            clearInterval(this.healthTimer);
            this.healthTimer = null;
        }
        if (
            this.child &&
            (this.child.exitCode !== null || this.child.signalCode !== null)
        ) {
            this.child = null;
        }
        this.workerConcurrency = null;
        this.state = 'stopped';
        this.onState?.(this.getStatus());
    }

    async request(
        relativePath,
        { method = 'GET', body, headers = {}, internal = false } = {},
    ) {
        await this.start();
        const secrets = internal ? await this.getSecrets() : null;
        const response = await fetch(`${this.baseUrl}${relativePath}`, {
            method,
            headers: {
                ...headers,
                ...(body === undefined ? {} : { 'Content-Type': 'application/json' }),
                ...(internal
                    ? {
                        'X-Finance-Desktop-Token': secrets.controlToken,
                    }
                    : {}),
            },
            body: body === undefined ? undefined : JSON.stringify(body),
        });
        return response;
    }

    async stop() {
        if (this.stopPromise) {
            return this.stopPromise;
        }
        this.stopPromise = this.stopService();
        try {
            return await this.stopPromise;
        } finally {
            this.stopPromise = null;
        }
    }

    async stopService() {
        const child = this.child;
        if (!child && this.serverPid === null && !this.pidFile) {
            this.state = 'stopped';
            return { warning: null };
        }

        let expectedPid = this.serverPid;
        if (expectedPid === null && this.pidFile) {
            try {
                const pidText = await readFile(this.pidFile, 'utf8');
                const pidFromFile = Number(pidText.trim());
                expectedPid = Number.isSafeInteger(pidFromFile)
                    ? pidFromFile
                    : null;
            } catch (error) {
                if (error.code !== 'ENOENT') {
                    throw error;
                }
            }
        }

        this.state = 'stopping';
        if (this.healthTimer) {
            clearInterval(this.healthTimer);
            this.healthTimer = null;
        }
        this.onState?.(this.getStatus());
        let warning = null;
        try {
            const closeResult = await this.#runCli([
                ...this.baseArguments,
                'api',
                'close',
                '--host',
                '127.0.0.1',
                '--port',
                String(this.port),
                '--pid-file',
                this.pidFile,
            ]);
            if (closeResult.code !== 0) {
                warning = closeResult.stderr || closeResult.stdout;
            }
        } catch (error) {
            warning = error.message;
        }

        const controlToken = (await this.getSecrets()).controlToken;
        let serverStopped = this.baseUrl === null;
        const deadline = Date.now() + 10_000;
        while (!serverStopped && Date.now() < deadline) {
            try {
                const response = await fetch(
                    `${this.baseUrl}/desktop/health`,
                    {
                        headers: {
                            'X-Finance-Desktop-Token': controlToken,
                        },
                        signal: AbortSignal.timeout(1_000),
                    },
                );
                if (response.status === 403) {
                    throw new Error(
                        'The local API rejected its installation control token during shutdown.',
                    );
                }
                if (response.status === 200) {
                    const health = await response.json();
                    if (expectedPid === null) {
                        throw new Error(
                            'Cannot verify the local API process before shutdown.',
                        );
                    }
                    serverStopped = health.process_id !== expectedPid;
                }
            } catch (error) {
                if (
                    error instanceof TypeError ||
                    error.name === 'TimeoutError' ||
                    error.name === 'AbortError'
                ) {
                    serverStopped = true;
                } else {
                    throw error;
                }
            }
            if (!serverStopped) {
                await delay(250);
            }
        }
        if (!serverStopped) {
            if (child && expectedPid === child.pid) {
                child.kill();
                await Promise.race([this.exitPromise, delay(5_000)]);
                serverStopped = true;
            }
        }
        if (!serverStopped) {
            throw new Error('Finance Scraper API did not stop after api close.');
        }
        if (child && child.exitCode === null) {
            child.kill();
            await Promise.race([this.exitPromise, delay(5_000)]);
        }
        this.child = null;
        this.baseUrl = null;
        this.port = null;
        this.pidFile = null;
        this.serverPid = null;
        this.workerConcurrency = null;
        this.state = 'stopped';
        this.onState?.(this.getStatus());
        return { warning };
    }

    async #runCli(args) {
        return new Promise((resolve, reject) => {
            const child = spawn(this.executable, args, {
                cwd: this.workingDirectory,
                env: this.environment,
                stdio: ['ignore', 'pipe', 'pipe'],
                windowsHide: true,
                shell: false,
            });
            let stdout = '';
            let stderr = '';
            child.stdout.setEncoding('utf8');
            child.stderr.setEncoding('utf8');
            child.stdout.on('data', (chunk) => {
                stdout = appendOutput(stdout, chunk);
            });
            child.stderr.on('data', (chunk) => {
                stderr = appendOutput(stderr, chunk);
            });
            child.once('error', reject);
            child.once('close', (code, signal) => {
                resolve({ code, signal, stdout, stderr });
            });
        });
    }
}
