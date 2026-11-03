import assert from 'node:assert/strict';
import test from 'node:test';

import { FinanceApiClient } from '../electron/services/api-client.js';

function jsonResponse(value, status = 200) {
    return new Response(
        value === null ? '' : JSON.stringify(value),
        {
            status,
            headers: { 'content-type': 'application/json' },
        },
    );
}

class FakeApiManager {
    calls = [];

    async request(endpoint, options) {
        this.calls.push({ endpoint, options });
        if (endpoint === '/auth/login') {
            return jsonResponse({
                access_token: 'access-one',
                refresh_token: 'refresh-one',
                expires_in: 900,
            });
        }
        if (endpoint === '/auth/refresh') {
            return jsonResponse({
                access_token: 'access-two',
                refresh_token: 'refresh-two',
                expires_in: 900,
            });
        }
        if (endpoint === '/accounts/me') {
            return jsonResponse({
                id: 'account-one',
                name: 'Owner',
                email: 'owner@example.com',
                role: 'user',
                language: { code: 'es', name: 'Español', style: 'friendly' },
                custom_report: [],
                watchlist: [],
            });
        }
        if (endpoint === '/reports/me') {
            return jsonResponse({ items: [], pagination: { total: 0 } });
        }
        if (endpoint === '/portfolio/me') {
            return jsonResponse({ success: true, portfolio: [] });
        }
        if (endpoint === '/portfolio/me/trades') {
            return jsonResponse(
                { success: true, portfolio: [] },
                201,
            );
        }
        if (endpoint === '/auth/logout') {
            return jsonResponse({ success: true });
        }
        if (endpoint === '/auth/register') {
            return jsonResponse({
                success: true,
                id: 'new-account',
                role: 'user',
            }, 201);
        }
        return jsonResponse(
            {
                error: 'NOT_FOUND',
                message: 'Not found',
                status_code: 404,
            },
            404,
        );
    }
}

test('sessions stay in the main process and refresh before API requests', async () => {
    const apiManager = new FakeApiManager();
    const client = new FinanceApiClient(apiManager);
    const profile = await client.login({
        email: 'owner@example.com',
        password: 'password',
    });

    assert.equal(profile.id, 'account-one');
    assert.equal(client.getProfile().email, 'owner@example.com');
    assert.deepEqual(
        apiManager.calls.find((call) => call.endpoint === '/auth/login')
            .options.headers,
        {},
    );

    client.session.expiresAt = Date.now() - 1;
    await client.request('/reports/me', { auth: true });
    const reportRequest = apiManager.calls.at(-1);
    assert.equal(reportRequest.options.headers.Authorization, 'Bearer access-two');
    assert.equal(client.session.refreshToken, 'refresh-two');

    await client.logout();
    assert.equal(client.getProfile(), null);
    const callCount = apiManager.calls.length;
    await assert.rejects(
        client.request('/reports/me', { auth: true }),
        { code: 'SESSION_REQUIRED' },
    );
    assert.equal(apiManager.calls.length, callCount);
});

test('local registration uses the internal bridge and does not expose session tokens', async () => {
    const apiManager = new FakeApiManager();
    const client = new FinanceApiClient(apiManager);

    const account = await client.register({
        name: 'New Owner',
        email: 'new@example.com',
        password: 'password',
        language: 'en',
    });

    assert.equal(account.role, 'user');
    assert.equal(client.getProfile(), null);
    assert.deepEqual(
        apiManager.calls[0].options.body,
        {
            name: 'New Owner',
            email: 'new@example.com',
            password: 'password',
            language: {
                code: 'en',
                name: 'English',
                style: 'friendly',
            },
        },
    );
    assert.equal(apiManager.calls[0].options.internal, true);
});

test('portfolio reads and trades use the authenticated account API', async () => {
    const apiManager = new FakeApiManager();
    const client = new FinanceApiClient(apiManager);
    await client.login({
        email: 'owner@example.com',
        password: 'password',
    });

    const trade = {
        action: 'BUY',
        ticker: 'AAPL',
        region: 'US',
        currency: 'USD',
        price: 184.5,
        quantity: 2,
        date: '2026-10-18',
    };
    await client.getPortfolio();
    await client.createPortfolioTrade(trade);

    const portfolioRead = apiManager.calls.find(
        (call) => call.endpoint === '/portfolio/me',
    );
    const tradeWrite = apiManager.calls.find(
        (call) => call.endpoint === '/portfolio/me/trades',
    );
    assert.equal(portfolioRead.options.headers.Authorization, 'Bearer access-one');
    assert.equal(tradeWrite.options.headers.Authorization, 'Bearer access-one');
    assert.deepEqual(tradeWrite.options.body, trade);
});
