import type { ReactNode } from 'react';

interface SettingsPanelProps {
    icon: ReactNode;
    label: string;
    title: string;
    wide?: boolean;
    children: ReactNode;
}

export function SettingsPanel({
    icon,
    label,
    title,
    wide = false,
    children,
}: SettingsPanelProps) {
    return (
        <section
            className={`content-panel settings-panel ${wide ? 'settings-wide' : ''}`}
        >
            <div className='panel-heading-row'>
                <div>
                    <p className='field-kicker'>
                        {icon}
                        {label}
                    </p>
                    <h2>{title}</h2>
                </div>
            </div>
            {children}
        </section>
    );
}
