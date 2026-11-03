
import type { Locale } from '#/types.js';
import { AiProviderKeysPanel } from '@/features/ai-providers/components/AiProviderKeysPanel.js';
import { CommandDialog } from '@/features/command-palette/components/CommandDialog.js';
import { translate } from '@/features/common/i18n/messages.js';


interface ConfigureApiKeysProps {
    isOpen: boolean;
    locale: Locale;
    returnFocusTarget: HTMLElement | null;
    onClose: () => void;
}

export function ConfigureApiKeys({
    isOpen,
    locale,
    returnFocusTarget,
    onClose,
}: ConfigureApiKeysProps) {
    return (
        <CommandDialog
            description={translate(locale, 'settings.aiProvidersCopy')}
            isOpen={isOpen}
            locale={locale}
            onClose={onClose}
            returnFocusTarget={returnFocusTarget}
            title={translate(locale, 'settings.apiKeys')}
        >
            {isOpen && (
                <AiProviderKeysPanel
                    idPrefix='command-provider'
                    locale={locale}
                    showIntro={false}
                />
            )}
        </CommandDialog>
    );
}
