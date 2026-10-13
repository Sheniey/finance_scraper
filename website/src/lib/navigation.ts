import { translations, type Locale } from '@/i18n'

export interface NavigationLink {
	label: string
	href: string
}

export interface NavigationMenu {
	label: string
	children: NavigationLink[]
}

export type NavigationItem = NavigationLink | NavigationMenu

export type LocalizedRoute =
	| 'home'
	| 'docs'
	| 'contact'

export const localizedRoute = (locale: Locale, route: LocalizedRoute) =>
	`/${locale}/${route}`

export function getNavigationItems(locale: Locale): NavigationItem[] {
	const t = translations(locale)

	return [
		{ label: t({ mnemonic: 'nav.home' }), href: localizedRoute(locale, 'home') },
		{ label: t({ mnemonic: 'nav.docs' }), href: localizedRoute(locale, 'docs') },
		{ label: t({ mnemonic: 'nav.contact' }), href: localizedRoute(locale, 'contact') },
	]
}
