
import type { ReportEntry } from '#/types.js';
import { LoadingSpinner } from '@/features/common/components/LoadingSpinner.js';



interface ReportStatusIndicatorProps {
    status: ReportEntry['status'];
}


export function ReportStatusIndicator({
    status,
}: ReportStatusIndicatorProps) {
    if (status === 'PENDING' || status === 'IN_PROGRESS') {
        return (
            <LoadingSpinner
                className='status-chip-spinner'
                size={12}
            />
        );
    }
    return <span className='status-chip-dot' />;
}
