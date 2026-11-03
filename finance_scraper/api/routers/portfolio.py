from fastapi import APIRouter, Depends, Response, status

from api.repositories import account as AccountRepository
from api.schemas.portfolio import PortfolioResponse, PortfolioTradeCreate
from api.services.security import require_permission
from finance.services.account import Account
from finance.services.account.models import Stock


router: APIRouter = APIRouter(prefix='/portfolio', tags=['portfolio'])


def _portfolio_response(account: Account) -> PortfolioResponse:
    return PortfolioResponse(
        portfolio=[
            holding
            for holding in account.portfolio
            if isinstance(holding, Stock)
        ],
    )


@router.get(
    '/me',
    response_model=PortfolioResponse,
    summary='Get the authenticated account portfolio and trade history',
)
async def get_my_portfolio(
    account: Account = Depends(require_permission('account-me:read')),
) -> PortfolioResponse:
    return _portfolio_response(account)


@router.post(
    '/me/trades',
    response_model=PortfolioResponse,
    status_code=status.HTTP_201_CREATED,
    summary='Record a buy or sell trade for the authenticated account',
)
async def create_my_portfolio_trade(
    payload: PortfolioTradeCreate,
    response: Response,
    account: Account = Depends(require_permission('account-me:update')),
) -> PortfolioResponse:
    updated_account: Account = await AccountRepository.add_portfolio_trade(
        account,
        payload,
    )
    response.headers['Location'] = '/portfolio/me'
    return _portfolio_response(updated_account)
