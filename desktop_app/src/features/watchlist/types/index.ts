
import type { UserProfile } from '#/types.js';

export type AddWatchlistTickerResult =
    | { status: 'added'; profile: UserProfile; ticker: string }
    | { status: 'duplicate'; ticker: string }
    | { status: 'empty'; ticker: string };
