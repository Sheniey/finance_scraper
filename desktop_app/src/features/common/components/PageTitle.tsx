
export interface PageTitleProps {
    sectionName: string,
    title: string,
    copy: string
}


export function PageTitle({
    sectionName,
    title,
    copy
}: PageTitleProps) {
    return (
        <div className='page-title'>
            <p className='eyebrow dark'>
                <span className='signal-mark' />
                {sectionName}
            </p>
            <h1>{title}</h1>
            <p>{copy}</p>
        </div>
    )
}

export default PageTitle;
