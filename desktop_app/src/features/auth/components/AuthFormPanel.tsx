
import { useState, type SubmitEvent } from 'react';
import {
    ArrowRight,
    KeyRound,
    UserRound,
} from 'lucide-react';

import type { Locale } from '#/types.js';
import { formatError, translate } from '@/features/common/i18n/messages.js';

import { AuthCredentialFields } from '@/features/auth/components/AuthCredentialFields.js';
import type { AuthMode } from '@/features/auth/types/index.js';



interface AuthFormPanelProps {
    locale: Locale;
    isOnline: boolean;
    initialError: string | null;
    onLogin: (credentials: { email: string; password: string }) => Promise<void>;
    onRegister: (credentials: {
        name: string;
        email: string;
        password: string;
        language: Locale;
    }) => Promise<void>;
}


export function AuthFormPanel({
    locale,
    isOnline,
    initialError,
    onLogin,
    onRegister,
}: AuthFormPanelProps) {
    const [mode, setMode] = useState<AuthMode>('login');
    const [name, setName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [notice, setNotice] = useState<string | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const t = (key: string) => translate(locale, key);

    async function submit(event: SubmitEvent<HTMLFormElement>) {
        event.preventDefault();
        setError(null);
        setNotice(null);
        if (!isOnline) {
            setError(t('auth.apiRequired'));
            return;
        }
        if (mode === 'register' && password !== confirmPassword) {
            setError(t('auth.passwordMismatch'));
            return;
        }

        setIsSubmitting(true);
        try {
            if (mode === 'login') {
                await onLogin({ email: email.trim(), password });
            } else {
                await onRegister({
                    name: name.trim(),
                    email: email.trim(),
                    password,
                    language: locale,
                });
                setPassword('');
                setConfirmPassword('');
                setShowPassword(false);
                setShowConfirmPassword(false);
                setMode('login');
                setNotice(t('auth.registered'));
            }
        } catch (requestError) {
            setError(formatError(locale, requestError));
        } finally {
            setIsSubmitting(false);
        }
    }

    function changeMode(nextMode: AuthMode) {
        setMode(nextMode);
        setError(null);
        setNotice(null);
        setShowPassword(false);
        setShowConfirmPassword(false);
    }

    return (
        <section className='auth-form-panel'>
            <div className='auth-form-heading'>
                <span className='auth-form-icon'>
                    {mode === 'login' ? (
                        <KeyRound size={19} />
                    ) : (
                        <UserRound size={19} />
                    )}
                </span>
                <div>
                    <p className='field-kicker'>
                        {mode === 'login' ? t('auth.login') : t('auth.register')}
                    </p>
                    <h2>
                        {mode === 'login'
                            ? t('auth.loginTitle')
                            : t('auth.registerTitle')}
                    </h2>
                </div>
            </div>
            <p className='auth-form-copy'>
                {mode === 'login'
                    ? t('auth.loginCopy')
                    : t('auth.registerCopy')}
            </p>

            <form className='auth-form' onSubmit={submit}>
                <AuthCredentialFields
                    confirmPassword={confirmPassword}
                    email={email}
                    locale={locale}
                    mode={mode}
                    name={name}
                    onConfirmPasswordChange={setConfirmPassword}
                    onEmailChange={setEmail}
                    onNameChange={setName}
                    onPasswordChange={setPassword}
                    onToggleConfirmPasswordVisibility={() =>
                        setShowConfirmPassword((visible) => !visible)
                    }
                    onTogglePasswordVisibility={() =>
                        setShowPassword((visible) => !visible)
                    }
                    password={password}
                    showConfirmPassword={showConfirmPassword}
                    showPassword={showPassword}
                />

                {(error || initialError) && (
                    <p className='form-message error-message' role='alert'>
                        {error ?? initialError}
                    </p>
                )}
                {notice && (
                    <p className='form-message success-message' role='status'>
                        {notice}
                    </p>
                )}
                <button
                    className='button-primary auth-submit'
                    disabled={!isOnline || isSubmitting}
                    type='submit'
                >
                    {isSubmitting
                        ? t('common.loading')
                        : mode === 'login'
                            ? t('auth.loginAction')
                            : t('auth.registerAction')}
                    <ArrowRight size={16} aria-hidden='true' />
                </button>
            </form>

            <p className='auth-mode-switch'>
                {mode === 'login' ? t('auth.toRegister') : t('auth.toLogin')}
                <button
                    onClick={() =>
                        changeMode(mode === 'login' ? 'register' : 'login')
                    }
                    type='button'
                >
                    {mode === 'login'
                        ? t('auth.createAccount')
                        : t('auth.backToLogin')}
                </button>
            </p>
        </section>
    );
}
