import { access, mkdir, readFile, rename, writeFile } from 'node:fs/promises';
import path from 'node:path';

const PROVIDER_VARIABLES = Object.freeze({
    openai: 'OPENAI_API_KEY',
    deepseek: 'DEEPSEEK_API_KEY',
    anthropic: 'ANTHROPIC_API_KEY',
});

const VARIABLE_TO_PROVIDER = Object.freeze(
    Object.fromEntries(
        Object.entries(PROVIDER_VARIABLES).map(([provider, variable]) => [
            variable,
            provider,
        ]),
    ),
);

function parseEnvValue(rawValue) {
    const value = rawValue.replace(/\s+#.*$/, '').trim();
    if (!value) {
        return '';
    }

    if (value.startsWith('"') && value.endsWith('"')) {
        try {
            return JSON.parse(value);
        } catch {
            throw new Error('The local provider key file contains an invalid value.');
        }
    }
    if (value.startsWith("'") && value.endsWith("'")) {
        return value.slice(1, -1).replaceAll("\\'", "'");
    }
    return value;
}

function parseProviderKeys(contents) {
    const values = {};
    for (const line of contents.split(/\r?\n/)) {
        const match = line.match(/^\s*(?:export\s+)?([A-Z_]+)\s*=\s*(.*)$/);
        if (!match || !(match[1] in VARIABLE_TO_PROVIDER)) {
            continue;
        }
        const provider = VARIABLE_TO_PROVIDER[match[1]];
        values[provider] = parseEnvValue(match[2]);
    }
    return values;
}

async function readEnvFile(directory) {
    const filePath = path.join(directory, '.env');
    try {
        await access(filePath);
    } catch (error) {
        if (error.code === 'ENOENT') {
            return { filePath, contents: '' };
        }
        throw error;
    }
    return {
        filePath,
        contents: await readFile(filePath, 'utf8'),
    };
}

export async function readAiProviderKeys(directory) {
    const { contents } = await readEnvFile(directory);
    return parseProviderKeys(contents);
}

export async function getAiProviderStatus(directory) {
    const keys = await readAiProviderKeys(directory);
    return {
        openai: Boolean(keys.openai),
        deepseek: Boolean(keys.deepseek),
        anthropic: Boolean(keys.anthropic),
    };
}

function validateUpdates(updates) {
    if (!updates || typeof updates !== 'object' || Array.isArray(updates)) {
        throw new Error('Provider key updates must be an object.');
    }

    const normalized = new Map();
    for (const [provider, value] of Object.entries(updates)) {
        const variable = PROVIDER_VARIABLES[provider];
        if (!variable) {
            throw new Error(`Unsupported AI provider: ${provider}`);
        }
        if (value !== null && typeof value !== 'string') {
            throw new Error(`The ${provider} key must be text or null.`);
        }
        if (
            typeof value === 'string' &&
            (value.length > 8_192 || /[\r\n\0]/.test(value))
        ) {
            throw new Error(`The ${provider} key has an invalid format.`);
        }
        normalized.set(variable, value);
    }
    return normalized;
}

export async function saveAiProviderKeys(directory, updates) {
    const normalizedUpdates = validateUpdates(updates);
    if (normalizedUpdates.size === 0) {
        return getAiProviderStatus(directory);
    }

    const { filePath, contents } = await readEnvFile(directory);
    const newline = contents.includes('\r\n') ? '\r\n' : '\n';
    const lines = contents ? contents.split(/\r?\n/) : [];
    if (lines.at(-1) === '') {
        lines.pop();
    }

    const updatedVariables = new Set();
    const nextLines = [];
    for (const line of lines) {
        const match = line.match(/^\s*(?:export\s+)?([A-Z_]+)\s*=/);
        const variable = match?.[1];
        if (!variable || !normalizedUpdates.has(variable)) {
            nextLines.push(line);
            continue;
        }
        if (updatedVariables.has(variable)) {
            continue;
        }
        updatedVariables.add(variable);
        const value = normalizedUpdates.get(variable);
        if (typeof value === 'string') {
            nextLines.push(`${variable}=${JSON.stringify(value)}`);
        }
    }

    for (const [variable, value] of normalizedUpdates) {
        if (!updatedVariables.has(variable) && typeof value === 'string') {
            nextLines.push(`${variable}=${JSON.stringify(value)}`);
        }
    }

    await mkdir(directory, { recursive: true });
    const temporaryPath = `${filePath}.${process.pid}.tmp`;
    const serialized = nextLines.length
        ? `${nextLines.join(newline)}${newline}`
        : '';
    await writeFile(temporaryPath, serialized, {
        encoding: 'utf8',
        mode: 0o600,
    });
    await rename(temporaryPath, filePath);

    return getAiProviderStatus(directory);
}
