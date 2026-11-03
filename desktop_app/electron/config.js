
import {
    app,
} from 'electron';
import path from 'path';


export const APP_NAME = 'Finance Scraper';
export const APP_NAME_SHORT = 'FSCRAPER';
export const APP_NAME_CODING = 'finance_scraper';
export const APP_NAME_CODING_2 = 'finance-scraper';

export const API_BACKEND_URL = new Set(['http://127.0.0.1:5173', 'http://localhost:5173']);


export const ISOLATED_USER_DATA_PATH = !app.isPackaged && process.env.FINANCE_DESKTOP_USER_DATA;
export const USER_APPDATA_PATH = ISOLATED_USER_DATA_PATH
    ? path.resolve(ISOLATED_USER_DATA_PATH)
    : path.join(app.getPath('appData'), APP_NAME);
export const SESSION_DATA_PATH = path.join(USER_APPDATA_PATH, 'Session Data');
