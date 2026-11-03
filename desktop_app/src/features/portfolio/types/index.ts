
import type {
    CreatePortfolioTradeRequest,
    PortfolioAction,
    PortfolioHolding,
} from '#/types.js';

export interface PortfolioTradeDraft {
    action: 'BUY' | 'SELL';
    ticker: string;
    region: string;
    currency: string;
    price: string;
    quantity: string;
    date: string;
}

export type PortfolioTradeValidation =
    | { ok: true; request: CreatePortfolioTradeRequest }
    | {
          ok: false;
          errorKey:
              | 'portfolio.tickerRequired'
              | 'portfolio.priceInvalid'
              | 'portfolio.quantityInvalid';
      };

export interface PortfolioTradeRow {
    holding: PortfolioHolding;
    action: PortfolioAction;
    key: string;
}
