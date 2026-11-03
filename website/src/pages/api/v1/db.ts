
import type { APIRoute } from 'astro';
import { DB_URI, DB_TOKEN, DB_TYPE, DB_PROVIDER } from 'astro:env/server';

export const GET: APIRoute = async () => {
    return new Response(
        JSON.stringify({
            success: true,
            payload: {
                uri: DB_URI,
                token: DB_TOKEN,
                type: DB_TYPE,
                provider: DB_PROVIDER
            },
            error: null // this never occurs, dang
        }),
        {
            status: 200,
            headers: {
                'Content-Type': 'application/json'
            }
        }
    );
};
