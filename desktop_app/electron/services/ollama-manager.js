
import { spawn, spawnSync } from 'node:child_process';
import { access } from 'node:fs/promises';
import path from 'node:path';

const OLLAMA_TAGS_URL = 'http://127.0.0.1:11434/api/tags';
const PROBE_TIMEOUT_MS = 1_500;
const START_TIMEOUT_MS = 20_000;
const START_POLL_MS = 500;
const MAX_INSTALL_OUTPUT = 4_000;

function delay(milliseconds) {
    return new Promise((resolve) => setTimeout(resolve, milliseconds));
}

function ollamaCandidates(platform) {
    if (platform === 'win32') {
        return [
            process.env.LOCALAPPDATA
                ? path.join(
                      process.env.LOCALAPPDATA,
                      'Programs',
                      'Ollama',
                      'ollama.exe',
                  )
                : null,
            process.env.PROGRAMFILES
                ? path.join(process.env.PROGRAMFILES, 'Ollama', 'ollama.exe')
                : null,
            'ollama.exe',
        ].filter(Boolean);
    }
    if (platform === 'darwin') {
        return [
            '/Applications/Ollama.app/Contents/Resources/ollama',
            'ollama',
        ];
    }
    if (platform === 'linux') {
        return ['ollama'];
    }
    throw new Error(`Ollama is not supported on ${platform}.`);
}

function isCommandName(candidate) {
    return !candidate.includes(path.sep);
}

async function resolveOllamaExecutable() {
    for (const candidate of ollamaCandidates(process.platform)) {
        if (isCommandName(candidate)) {
            const result = spawnSync(candidate, ['--version'], {
                encoding: 'utf8',
                timeout: PROBE_TIMEOUT_MS,
                windowsHide: true,
                shell: false,
            });
            if (!result.error && result.status === 0) {
                return candidate;
            }
            if (
                result.error &&
                result.error.code !== 'ENOENT' &&
                result.error.code !== 'ENOTDIR'
            ) {
                throw result.error;
            }
            continue;
        }

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

function isOllamaUnavailable(error) {
    if (error?.name === 'TimeoutError' || error?.name === 'AbortError') {
        return true;
    }
    const causeCode = error?.cause?.code;
    return (
        error instanceof TypeError &&
        ['ECONNREFUSED', 'ECONNRESET', 'ENOTFOUND'].includes(causeCode)
    );
}

async function readOllamaModels() {
    let response;
    try {
        response = await fetch(OLLAMA_TAGS_URL, {
            signal: AbortSignal.timeout(PROBE_TIMEOUT_MS),
        });
    } catch (error) {
        if (isOllamaUnavailable(error)) {
            return null;
        }
        throw error;
    }
    if (!response.ok) {
        throw new Error(
            `Ollama status check failed with HTTP ${response.status}.`,
        );
    }

    const payload = await response.json();
    if (
        !payload ||
        typeof payload !== 'object' ||
        !Array.isArray(payload.models) ||
        !payload.models.every(
            (model) =>
                model &&
                typeof model === 'object' &&
                typeof model.name === 'string',
        )
    ) {
        throw new Error('Ollama returned an invalid model list.');
    }
    return payload.models.map((model) => model.name);
}

export async function getOllamaStatus() {
    const [executable, models] = await Promise.all([
        resolveOllamaExecutable(),
        readOllamaModels(),
    ]);
    return {
        installed: Boolean(executable) || models !== null,
        running: models !== null,
        models: models ?? [],
        platform: process.platform,
    };
}

function installerCommand(platform) {
    if (platform === 'win32') {
        return {
            executable: 'powershell.exe',
            arguments: [
                '-NoProfile',
                '-ExecutionPolicy',
                'Bypass',
                '-Command',
                'irm https://ollama.com/install.ps1 | iex',
            ],
        };
    }
    if (platform === 'darwin' || platform === 'linux') {
        return {
            executable: '/bin/sh',
            arguments: [
                '-c',
                'curl -fsSL https://ollama.com/install.sh | sh',
            ],
        };
    }
    throw new Error(`Ollama installation is not supported on ${platform}.`);
}

function safeInstallerEnvironment() {
    const allowedVariables = [
        'APPDATA',
        'COMSPEC',
        'HOME',
        'LANG',
        'LOCALAPPDATA',
        'LOGNAME',
        'PATH',
        'PATHEXT',
        'PROGRAMFILES',
        'PROGRAMFILES(X86)',
        'SHELL',
        'SYSTEMROOT',
        'TEMP',
        'TMP',
        'TMPDIR',
        'USER',
        'USERPROFILE',
        'WINDIR',
    ];
    const environment = {};
    for (const variable of allowedVariables) {
        const value = process.env[variable];
        if (value) {
            environment[variable] = value;
        }
    }
    return environment;
}

function runInstaller(command) {
    return new Promise((resolve, reject) => {
        const child = spawn(command.executable, command.arguments, {
            env: safeInstallerEnvironment(),
            shell: false,
            stdio: ['ignore', 'pipe', 'pipe'],
            windowsHide: true,
        });
        let output = '';
        const appendOutput = (chunk) => {
            output = `${output}${chunk}`.slice(-MAX_INSTALL_OUTPUT);
        };
        child.stdout.setEncoding('utf8');
        child.stderr.setEncoding('utf8');
        child.stdout.on('data', appendOutput);
        child.stderr.on('data', appendOutput);
        child.once('error', reject);
        child.once('close', (code) => {
            if (code === 0) {
                resolve(output);
                return;
            }
            reject(
                new Error(
                    `Ollama installation failed with exit code ${code ?? 'unknown'}.${
                        output ? `\n${output}` : ''
                    }`,
                ),
            );
        });
    });
}

export async function installOllama() {
    const command = installerCommand(process.platform);
    await runInstaller(command);
    return getOllamaStatus();
}

export async function startOllama() {
    const status = await getOllamaStatus();
    if (status.running) {
        return status;
    }
    const executable = await resolveOllamaExecutable();
    if (!executable) {
        throw new Error('Ollama is not installed.');
    }

    const child = spawn(executable, ['serve'], {
        env: safeInstallerEnvironment(),
        shell: false,
        stdio: 'ignore',
        windowsHide: true,
    });
    let startupError = null;
    child.once('error', (error) => {
        startupError = error;
    });
    child.once('exit', (code) => {
        if (code !== 0) {
            startupError = new Error(
                `Ollama stopped during startup with exit code ${code ?? 'unknown'}.`,
            );
        }
    });
    child.unref();

    const deadline = Date.now() + START_TIMEOUT_MS;
    while (Date.now() < deadline) {
        if (startupError) {
            throw startupError;
        }
        const nextStatus = await getOllamaStatus();
        if (nextStatus.running) {
            return nextStatus;
        }
        await delay(START_POLL_MS);
    }
    if (startupError) {
        throw startupError;
    }
    throw new Error('Ollama did not start in time.');
}
