
import type { APIRoute } from 'astro';
import { BINARY_CURRENT_VERSION, BINARY_DOWNLOAD_URL } from 'astro:env/client';

export const GET: APIRoute = async () => {
    return new Response(
        JSON.stringify({
            success: true,
            downloadUrl:
                BINARY_DOWNLOAD_URL.replace('{baseUrl}', import.meta.env.BASE_URL),
            currentVersion: BINARY_CURRENT_VERSION,
        }),
        {
            status: 200,
            headers: {
                'Content-Type': 'application/json',
                'X-Current-Version': BINARY_CURRENT_VERSION
            }
        }
    );
};
