
import type { OllamaStatus } from '#/types.js';

const OLLAMA_STATUS_EVENT = 'finance-scraper:ollama-status';

function isOllamaStatus(value: unknown): value is OllamaStatus {
    return (
        typeof value === 'object' &&
        value !== null &&
        'installed' in value &&
        typeof value.installed === 'boolean' &&
        'running' in value &&
        typeof value.running === 'boolean' &&
        'models' in value &&
        Array.isArray(value.models) &&
        value.models.every((model) => typeof model === 'string') &&
        'platform' in value &&
        typeof value.platform === 'string'
    );
}

export function announceOllamaStatus(status: OllamaStatus) {
    window.dispatchEvent(
        new CustomEvent<OllamaStatus>(OLLAMA_STATUS_EVENT, {
            detail: status,
        }),
    );
}

export function subscribeToOllamaStatus(
    callback: (status: OllamaStatus) => void,
): () => void {
    const listener = (event: Event) => {
        if (
            event instanceof CustomEvent &&
            isOllamaStatus(event.detail)
        ) {
            callback(event.detail);
        }
    };
    window.addEventListener(OLLAMA_STATUS_EVENT, listener);
    return () => window.removeEventListener(OLLAMA_STATUS_EVENT, listener);
}
