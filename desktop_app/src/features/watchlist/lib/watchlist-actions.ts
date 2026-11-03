
import type { UserProfile, WatchlistItem } from '#/types.js';
import type { AddWatchlistTickerResult } from '@/features/watchlist/types/index.js';

export async function addTickerToWatchlist(
    profile: UserProfile,
    value: string,
): Promise<AddWatchlistTickerResult> {
    const ticker = value.trim().toUpperCase();
    if (!ticker) {
        return { status: 'empty', ticker };
    }

    const items = profile.watchlist.filter(
        (item): item is WatchlistItem => Boolean(item),
    );
    if (items.some((item) => item.ticker === ticker)) {
        return { status: 'duplicate', ticker };
    }

    const updatedProfile = await window.desktopApi.updateProfile({
        ...profile,
        watchlist: [
            ...items,
            {
                ticker,
                region: 'US',
                mode: 'custom',
                llm_explanation: false,
                charts: true,
                horizon: 15,
                enabled: true,
            },
        ],
    });
    return { status: 'added', profile: updatedProfile, ticker };
}
