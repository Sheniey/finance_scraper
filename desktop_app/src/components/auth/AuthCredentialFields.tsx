import {
    Eye,
    EyeOff,
    LockKeyhole,
    Mail,
    ShieldCheck,
    UserRound,
} from 'lucide-react';

import type { AuthMode } from '@/components/auth/auth-types.js';
import { translate } from '@/i18n/messages.js';
import type { Locale } from '#/types.js';

interface AuthCredentialFieldsProps {
    locale: Locale;
    mode: AuthMode;
    name: string;
    email: string;
    password: string;
    confirmPassword: string;
    showPassword: boolean;
    showConfirmPassword: boolean;
    onNameChange: (value: string) => void;
    onEmailChange: (value: string) => void;
    onPasswordChange: (value: string) => void;
    onConfirmPasswordChange: (value: string) => void;
    onTogglePasswordVisibility: () => void;
    onToggleConfirmPasswordVisibility: () => void;
}

export function AuthCredentialFields({
    locale,
    mode,
    name,
    email,
    password,
    confirmPassword,
    showPassword,
    showConfirmPassword,
    onNameChange,
    onEmailChange,
    onPasswordChange,
    onConfirmPasswordChange,
    onTogglePasswordVisibility,
    onToggleConfirmPasswordVisibility,
}: AuthCredentialFieldsProps) {
    const t = (key: string) => translate(locale, key);

    return (
        <>
            {mode === 'register' && (
                <label className='form-field'>
                    <span>{t('auth.name')}</span>
                    <span className='field-control'>
                        <UserRound size={16} aria-hidden='true' />
                        <input
                            autoComplete='name'
                            maxLength={120}
                            onChange={(event) =>
                                onNameChange(event.target.value)
                            }
                            required
                            value={name}
                        />
                    </span>
                </label>
            )}
            <label className='form-field'>
                <span>{t('auth.email')}</span>
                <span className='field-control'>
                    <Mail size={16} aria-hidden='true' />
                    <input
                        autoComplete='email'
                        onChange={(event) =>
                            onEmailChange(event.target.value)
                        }
                        required
                        type='email'
                        value={email}
                    />
                </span>
            </label>
            <div className='form-field'>
                <label htmlFor='auth-password'>{t('auth.password')}</label>
                <span className='field-control'>
                    <LockKeyhole size={16} aria-hidden='true' />
                    <input
                        id='auth-password'
                        autoComplete={
                            mode === 'login'
                                ? 'current-password'
                                : 'new-password'
                        }
                        minLength={8}
                        onChange={(event) =>
                            onPasswordChange(event.target.value)
                        }
                        required
                        type={showPassword ? 'text' : 'password'}
                        value={password}
                    />
                    <button
                        aria-label={
                            showPassword
                                ? t('auth.hidePassword')
                                : t('auth.showPassword')
                        }
                        aria-pressed={showPassword}
                        className='password-visibility-button'
                        onClick={onTogglePasswordVisibility}
                        type='button'
                    >
                        {showPassword ? (
                            <EyeOff size={18} aria-hidden='true' />
                        ) : (
                            <Eye size={18} aria-hidden='true' />
                        )}
                    </button>
                </span>
            </div>
            {mode === 'register' && (
                <div className='form-field'>
                    <label htmlFor='auth-confirm-password'>
                        {t('auth.confirmPassword')}
                    </label>
                    <span className='field-control'>
                        <ShieldCheck size={16} aria-hidden='true' />
                        <input
                            id='auth-confirm-password'
                            autoComplete='new-password'
                            minLength={8}
                            onChange={(event) =>
                                onConfirmPasswordChange(event.target.value)
                            }
                            required
                            type={showConfirmPassword ? 'text' : 'password'}
                            value={confirmPassword}
                        />
                        <button
                            aria-label={
                                showConfirmPassword
                                    ? t('auth.hidePassword')
                                    : t('auth.showPassword')
                            }
                            aria-pressed={showConfirmPassword}
                            className='password-visibility-button'
                            onClick={onToggleConfirmPasswordVisibility}
                            type='button'
                        >
                            {showConfirmPassword ? (
                                <EyeOff size={18} aria-hidden='true' />
                            ) : (
                                <Eye size={18} aria-hidden='true' />
                            )}
                        </button>
                    </span>
                </div>
            )}
        </>
    );
}
