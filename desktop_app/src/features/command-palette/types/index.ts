
import type { LucideIcon } from 'lucide-react';

export type PaletteDialog =
    | 'createReport'
    | 'apiKeys'
    | 'watchlist'
    | 'language'
    | 'portfolioTrade'
    | 'google'
    | 'installOllama'
    | 'startOllama';

export interface PaletteCommandData {
    description: string;
    icon: LucideIcon;
    shortcut?: string[];
    execute: () => void;
}

export interface ResourceContextAction {
    id: string;
    label: string;
    icon: LucideIcon;
    danger?: boolean;
    disabled?: boolean;
    separatorBefore?: boolean;
    onSelect: () => void | Promise<void>;
}
