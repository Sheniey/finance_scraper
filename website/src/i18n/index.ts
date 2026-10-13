import { APP_NAME, LOCALES, SITE } from '@/config'
import englishCommon from './en/common.json'
import englishHome from './en/home.json'
import spanishCommon from './es/common.json'
import spanishHome from './es/home.json'

export type Locale = (typeof LOCALES)[number]
export type Mnemonic = keyof typeof spanishCommon | keyof typeof spanishHome

type Dictionary = Record<Mnemonic, string>

const dictionaries = {
	es: { ...spanishCommon, ...spanishHome },
	en: { ...englishCommon, ...englishHome },
} satisfies Record<Locale, Dictionary>

export function isLocale(value: string | undefined): value is Locale {
	return LOCALES.some((locale) => locale === value)
}

export function translations(locale: string) {
	if (!isLocale(locale)) {
		throw new Error(`Unsupported locale: ${locale}`)
	}

	const dictionary = dictionaries[locale]

	return ({ mnemonic }: { mnemonic: Mnemonic }) =>
		dictionary[mnemonic]
			.replaceAll('{{app_name}}', APP_NAME.fullname)
			.replaceAll('{{author}}', SITE.authorPseudonym)
}
