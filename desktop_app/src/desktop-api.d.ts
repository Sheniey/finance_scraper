import type { DesktopBridge } from '#/types.js';

declare global {
    interface Window {
        desktopApi: DesktopBridge;
    }
}

export {};
