// @ts-check
import { defineConfig, envField } from 'astro/config'
import react from '@astrojs/react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
	i18n: {
		locales: ['es', 'en'],
		defaultLocale: 'es',
		routing: {
			prefixDefaultLocale: true,
		},
	},
	vite: {
		plugins: [tailwindcss()],
	},
	integrations: [react()],
	env: {
		schema: {
			DB_URI: envField.string({ context: 'server', access: 'secret', optional: false }),
			DB_TOKEN: envField.string({ context: 'server', access: 'secret', optional: false }),
			DB_TYPE: envField.string({ context: 'server', access: 'secret', optional: true, default: 'sqlite' }),
			DB_PROVIDER: envField.string({ 'context': 'server', access: 'secret', optional: true }),

			BINARY_DOWNLOAD_URL: envField.string({ context: 'client', access: 'public', optional: true, default: '/' }),
			BINARY_CURRENT_VERSION: envField.string({ context: 'client', access: 'public', optional: true })
		}
	}
})