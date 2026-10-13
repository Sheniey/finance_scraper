
export const APP_NAME = {
    fullname: 'Finance Scraper',
    styled: 'finance_scraper',
    shorted: 'Finscrap',
    abbreviation: 'FS',
} as const;

export const LOCALES = ['en', 'es'] as const;
export const DEFAULT_LOCALE = 'es' as const;

export const SITE = {
    baseURL: 'https://finscrap.vercel.app',
    keywords: 'finance scraper,fs,fincrap,financial data,stock market,investments,portfolio,analysis,tracking',
    
    authorPseudonym: 'Sheñey',
    authorFirstName: 'José Daniel',
    authorLastName: 'Ávalos Becerra',
    authorIg: 'https://www.instagram.com/sheneyby2010_/',
    authorX: 'https://twitter.com/Sheney',
    authorGithub: 'https://github.com/Sheniey',
    authorLinkedIn: 'https://www.linkedin.com/in/sheney',
    authorYoutube: 'https://www.youtube.com/@Sheney',
    authorSpotify: 'https://open.spotify.com/user/sheney',

    favicon1: '/favicon.svg',
    favicon1Type: 'image/svg+xml',
    favicon2: '/favicon.ico',
    favicon2Type: 'image/x-icon',

    ogImage: '/og.jpg',
    ogImageAlt: 'Financial data overview',
    ogImageType: 'image/jpeg',
    ogType: 'website',
    
    twitterCard: 'summary_large_image',
    twitterCreator: '@Sheñey',

    repo: 'https://github.com/Sheniey/finance_scraper',
} as const;

export const BINARY_CURRENT_VERSION = '0.1.0';

export const formatPath = (path: string) => `/${path.replace(/^\/+/, '')}`;
export const formatStrictPath = (path: string) => `${SITE.baseURL}${formatPath(path)}`;
export const formatLocalePath = (locale: string, page: string) => `/${locale}/${page}`;
export const formatStrictLocalePath = (locale: string, page: string) => `${SITE.baseURL}/${locale}/${page}`;

export const MEDIA = {
    logo: {
        full: formatPath('icons/fs_logo.png'),
        fullBlack: formatPath('icons/fs_logo_black.png'),
        minimal: formatPath('icons/fs_minimal_px.svg'),
        banner: formatPath('icons/fs_banner_chart_hd_dark_px.png'),
    },
    favicon: {
        svg: formatStrictPath('/favicon.svg'),
        png: formatStrictPath('/favicon.png'),
    }
} as const;
