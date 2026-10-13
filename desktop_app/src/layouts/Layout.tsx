
import React from 'react';

export default async function PresentationLayout({ children }: { children: React.ReactNode }) {
    return (
        <div className='presentation-layout'>
            {children}
        </div>
    );
}
