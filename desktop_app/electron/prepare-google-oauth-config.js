
import { mkdir, writeFile } from 'node:fs/promises';
import path from 'node:path';


const clientId = process.env.GOOGLE_OAUTH_CLIENT_ID?.trim() ?? '';
if (
    clientId &&
    !/^[A-Za-z0-9-]+\.apps\.googleusercontent\.com$/.test(clientId)
) {
    throw new Error('GOOGLE_OAUTH_CLIENT_ID is not a valid desktop client ID.');
}

const outputPath = path.join(
    process.cwd(),
    'electron',
    'google-oauth-client.json',
);
await mkdir(path.dirname(outputPath), { recursive: true });
await writeFile(
    outputPath,
    `${JSON.stringify({ clientId }, null, 2)}\n`,
    { encoding: 'utf8', mode: 0o600 },
);
