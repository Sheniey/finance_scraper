import { app, safeStorage } from 'electron';
import { randomBytes } from 'node:crypto';
import { access, mkdir, readFile, rename, writeFile } from 'node:fs/promises';
import path from 'node:path';

let cachedVault;

function createInstallationSecrets() {
    return {
        controlToken: randomBytes(32).toString('base64url'),
        jwtSecretKey: randomBytes(48).toString('base64url'),
    };
}

async function writeVault(vault) {
    if (!safeStorage.isEncryptionAvailable()) {
        throw new Error('Windows secure storage is unavailable.');
    }
    const userData = app.getPath('userData');
    await mkdir(userData, { recursive: true });
    const target = path.join(userData, 'installation-vault.bin');
    const temporary = `${target}.${process.pid}.tmp`;
    const encrypted = safeStorage.encryptString(JSON.stringify(vault));
    await writeFile(temporary, encrypted, { mode: 0o600 });
    await rename(temporary, target);
}

export async function getInstallationSecrets() {
    if (cachedVault) {
        return cachedVault;
    }
    if (!safeStorage.isEncryptionAvailable()) {
        throw new Error('Windows secure storage is unavailable.');
    }

    const filePath = path.join(app.getPath('userData'), 'installation-vault.bin');
    try {
        await access(filePath);
    } catch (error) {
        if (error.code !== 'ENOENT') {
            throw error;
        }
        cachedVault = createInstallationSecrets();
        await writeVault(cachedVault);
        return cachedVault;
    }

    const encrypted = await readFile(filePath);
    const parsed = JSON.parse(safeStorage.decryptString(encrypted));
    if (
        typeof parsed.controlToken !== 'string' ||
        typeof parsed.jwtSecretKey !== 'string'
    ) {
        throw new Error('The local installation vault is invalid.');
    }
    cachedVault = parsed;
    return cachedVault;
}
