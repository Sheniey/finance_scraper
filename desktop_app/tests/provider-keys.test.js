import assert from 'node:assert/strict';
import { mkdtemp, readFile, rm, writeFile } from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import test from 'node:test';

import {
    getAiProviderStatus,
    readAiProviderKeys,
    saveAiProviderKeys,
} from '../electron/services/provider-keys.js';

test('provider key updates preserve unrelated .env values', async (context) => {
    const directory = await mkdtemp(
        path.join(os.tmpdir(), 'finance-scraper-provider-keys-'),
    );
    context.after(() => rm(directory, { recursive: true, force: true }));
    await writeFile(
        path.join(directory, '.env'),
        'EMAIL_ADDRESS=private@example.com\nOPENAI_API_KEY=old-key\nOTHER_VALUE=keep\n',
        'utf8',
    );

    const status = await saveAiProviderKeys(directory, {
        openai: 'new-key',
        deepseek: 'deep-key',
    });

    assert.deepEqual(status, {
        openai: true,
        deepseek: true,
        anthropic: false,
    });
    assert.deepEqual(await readAiProviderKeys(directory), {
        openai: 'new-key',
        deepseek: 'deep-key',
    });
    const contents = await readFile(path.join(directory, '.env'), 'utf8');
    assert.match(contents, /EMAIL_ADDRESS=private@example\.com/);
    assert.match(contents, /OTHER_VALUE=keep/);
    assert.match(contents, /OPENAI_API_KEY="new-key"/);
});

test('provider key updates can remove one key without clearing other providers', async (context) => {
    const directory = await mkdtemp(
        path.join(os.tmpdir(), 'finance-scraper-provider-keys-'),
    );
    context.after(() => rm(directory, { recursive: true, force: true }));
    await saveAiProviderKeys(directory, {
        openai: 'open-key',
        anthropic: 'anthropic-key',
    });

    const status = await saveAiProviderKeys(directory, { openai: null });

    assert.deepEqual(status, {
        openai: false,
        deepseek: false,
        anthropic: true,
    });
    assert.deepEqual(await readAiProviderKeys(directory), {
        anthropic: 'anthropic-key',
    });
});

test('provider key updates reject invalid keys without writing them', async (context) => {
    const directory = await mkdtemp(
        path.join(os.tmpdir(), 'finance-scraper-provider-keys-'),
    );
    context.after(() => rm(directory, { recursive: true, force: true }));

    await assert.rejects(
        saveAiProviderKeys(directory, { openai: 'key\nOTHER=secret' }),
        /invalid format/i,
    );
    assert.deepEqual(await getAiProviderStatus(directory), {
        openai: false,
        deepseek: false,
        anthropic: false,
    });
});
