
export const APP_NAME = {
    fullname: 'Finance Scraper',
    styled: 'finance_scraper',
    shorted: 'Finscrap',
    abbreviation: 'FS',
} as const;

export const LOCALES = ['en', 'es'] as const;

export const SITE = {
    baseURL: 'https://fincrap.vercel.app',
    keywords: 'finance scraper,fs,fincrap,financial data,stock market,investments,portfolio,analysis,tracking',
    
    authorPseudonym: 'Sheñey',
    authorFirstName: 'José Daniel',
    authorLastName: 'Ávalos Becerra',
    authorIg: 'https://www.instagram.com/sheneyby2010_/',
    
    favicon: '/favicon.svg',
    faviconType: 'image/svg+xml',
    
    ogImage: '/og.jpg',
    ogImageAlt: 'Financial data overview',
    ogImageType: 'image/jpeg',
    ogType: 'website',
    
    twitterCard: 'summary_large_image',
    twitterCreator: '@Sheñey',
} as const;

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
