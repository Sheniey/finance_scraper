
import type { CreatePortfolioTradeRequest } from '#/types.js';
import type {
    PortfolioTradeDraft,
    PortfolioTradeValidation,
} from '@/features/portfolio/types/index.js';

export function buildPortfolioTradeRequest(
    draft: PortfolioTradeDraft,
): PortfolioTradeValidation {
    const ticker = draft.ticker.trim().toUpperCase();
    const region = draft.region.trim().toUpperCase();
    const currency = draft.currency.trim().toUpperCase();
    const price = Number(draft.price);
    const quantity = Number(draft.quantity);

    if (!ticker) {
        return { ok: false, errorKey: 'portfolio.tickerRequired' };
    }
    if (!Number.isFinite(price) || price <= 0) {
        return { ok: false, errorKey: 'portfolio.priceInvalid' };
    }
    if (!Number.isSafeInteger(quantity) || quantity <= 0) {
        return { ok: false, errorKey: 'portfolio.quantityInvalid' };
    }

    return {
        ok: true,
        request: {
            action: draft.action,
            ticker,
            region,
            currency,
            price,
            quantity,
            date: draft.date,
        },
    };
}

export function localDateInputValue(): string {
    const now = new Date();
    const localTime = new Date(
        now.getTime() - now.getTimezoneOffset() * 60_000,
    );
    return localTime.toISOString().slice(0, 10);
}
