
import type {
    CreateReportRequest,
    Locale,
    ReportEntry,
    UserProfile,
} from '#/types.js';
import { AnalysisPage } from '@/pages/AnalysisPage.js';



interface CreateReportCommandProps {
    isOpen: boolean;
    locale: Locale;
    profile: UserProfile;
    onClose: () => void;
    onCreate: (request: CreateReportRequest) => Promise<ReportEntry>;
    onOpen: (report: ReportEntry) => Promise<void>;
    onReportsChanged: () => Promise<unknown>;
    onSaveCustomReport: (sections: string[]) => Promise<void>;
}


export function CreateReportCommand(props: CreateReportCommandProps) {
    return <AnalysisPage {...props} />;
}
