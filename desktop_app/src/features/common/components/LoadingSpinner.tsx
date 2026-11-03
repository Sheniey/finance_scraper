
import { motion } from 'motion/react';
import { LoaderCircle } from 'lucide-react';



interface LoadingSpinnerProps {
    size?: number;
    className?: string;
}


export function LoadingSpinner({
    size = 16,
    className,
}: LoadingSpinnerProps) {
    return (
        <motion.span
            animate={{ rotate: 360 }}
            aria-hidden='true'
            className={className}
            style={{ display: 'inline-flex' }}
            transition={{ duration: 0.72, ease: 'linear', repeat: Infinity }}
        >
            <LoaderCircle size={size} />
        </motion.span>
    );
}
