import { useCallback, useEffect, useMemo, useRef, useState, type ComponentProps } from 'react'
import { SRGBColorSpace, ShaderMaterial, TextureLoader, Vector2 } from 'three'
import type { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js'
import type { RenderPixelatedPass } from 'three/addons/postprocessing/RenderPixelatedPass.js'

const GLOBE_IMPORT_ERROR = 'Unable to load the interactive trading globe'
const EARTH_TEXTURE_LOAD_ERROR = 'Unable to load the Earth day and night textures'
const POST_PROCESSING_INIT_ERROR = 'Unable to initialize the globe CRT post-processing'

type GlobeComponentType = (typeof import('react-globe.gl'))['default']
type GlobeComponentRef = NonNullable<ComponentProps<GlobeComponentType>['ref']>
type GlobeHandle = NonNullable<GlobeComponentRef['current']>

interface TradingGlobeProps {
	label: string
	cityMexico: string
	cityNewYork: string
	cityLondon: string
	cityTokyo: string
}

interface Hub {
	lat: number
	lng: number
	color: string
	name?: string
}

interface ActivePostProcessing {
	globe: GlobeHandle
	composer: EffectComposer
	pixelatedPass: RenderPixelatedPass
}

const dayTextureUrl = 'https://cdn.jsdelivr.net/npm/three-globe/example/img/earth-day.jpg'
const nightTextureUrl = 'https://cdn.jsdelivr.net/npm/three-globe/example/img/earth-night.jpg'
const globeImageUrl = dayTextureUrl
const simulatedMinutesPerFrame = 1

const dayNightShader = {
	vertexShader: `
		varying vec3 vNormal;
		varying vec2 vUv;

		void main() {
			vNormal = normalize(normalMatrix * normal);
			vUv = uv;
			gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
		}
	`,
	fragmentShader: `
		#define PI 3.141592653589793

		uniform sampler2D dayTexture;
		uniform sampler2D nightTexture;
		uniform vec2 sunPosition;
		uniform vec2 globeRotation;
		varying vec3 vNormal;
		varying vec2 vUv;

		float toRad(float angle) {
			return angle * PI / 180.0;
		}

		vec3 polarToCartesian(vec2 coordinates) {
			float theta = toRad(90.0 - coordinates.x);
			float phi = toRad(90.0 - coordinates.y);
			return vec3(
				sin(phi) * cos(theta),
				cos(phi),
				sin(phi) * sin(theta)
			);
		}

		void main() {
			float inverseLongitude = toRad(globeRotation.x);
			float inverseLatitude = -toRad(globeRotation.y);
			mat3 rotationX = mat3(
				1.0, 0.0, 0.0,
				0.0, cos(inverseLatitude), -sin(inverseLatitude),
				0.0, sin(inverseLatitude), cos(inverseLatitude)
			);
			mat3 rotationY = mat3(
				cos(inverseLongitude), 0.0, sin(inverseLongitude),
				0.0, 1.0, 0.0,
				-sin(inverseLongitude), 0.0, cos(inverseLongitude)
			);
			vec3 sunDirection = rotationX * rotationY * polarToCartesian(sunPosition);
			float sunlight = dot(normalize(vNormal), normalize(sunDirection));
			float dayBlend = smoothstep(-0.12, 0.12, sunlight);
			vec4 dayColor = texture2D(dayTexture, vUv);
			vec4 nightColor = texture2D(nightTexture, vUv);
			gl_FragColor = mix(nightColor, dayColor, dayBlend);
		}
	`,
}

const fallbackRoutes = [
	'M92 281Q167 103 258 188',
	'M114 298Q214 138 309 206',
	'M127 309Q242 185 359 169',
	'M148 318Q232 216 383 215',
	'M167 307Q266 245 415 197',
	'M144 289Q195 155 327 148',
	'M176 319Q301 270 431 241',
	'M103 270Q251 113 371 179',
	'M189 295Q256 167 410 177',
	'M155 325Q281 210 448 214',
	'M116 316Q227 263 346 282',
	'M204 303Q307 168 430 148',
	'M96 299Q191 202 278 230',
	'M166 281Q266 125 395 198',
	'M130 326Q260 290 383 253',
	'M183 321Q306 237 437 184',
	'M121 285Q243 168 365 148',
	'M198 316Q290 278 423 261',
	'M107 308Q193 245 310 268',
	'M156 296Q284 148 447 184',
]

function getSunPosition(timestamp: number) {
	const date = new Date(timestamp)
	const yearStart = Date.UTC(date.getUTCFullYear(), 0, 1)
	const today = Date.UTC(date.getUTCFullYear(), date.getUTCMonth(), date.getUTCDate())
	const dayOfYear = Math.floor((today - yearStart) / 86_400_000) + 1
	const utcHour = date.getUTCHours() + date.getUTCMinutes() / 60 + date.getUTCSeconds() / 3600
	const fractionalYear = (2 * Math.PI / 365) * (dayOfYear - 1 + (utcHour - 12) / 24)
	const equationOfTime =
		229.18 *
		(0.000075 +
			0.001868 * Math.cos(fractionalYear) -
			0.032077 * Math.sin(fractionalYear) -
			0.014615 * Math.cos(2 * fractionalYear) -
			0.040849 * Math.sin(2 * fractionalYear))
	const declination =
		0.006918 -
		0.399912 * Math.cos(fractionalYear) +
		0.070257 * Math.sin(fractionalYear) -
		0.006758 * Math.cos(2 * fractionalYear) +
		0.000907 * Math.sin(2 * fractionalYear) -
		0.002697 * Math.cos(3 * fractionalYear) +
		0.00148 * Math.sin(3 * fractionalYear)

	return {
		longitude: (12 - utcHour) * 15 - equationOfTime / 4,
		latitude: declination * 180 / Math.PI,
	}
}

function createNetwork({
	cityMexico,
	cityNewYork,
	cityLondon,
	cityTokyo,
}: TradingGlobeProps) {
	const hubs: Hub[] = [
		{ name: cityMexico, lat: 19.4326, lng: -99.1332, color: '#ff7b35' },
		{ name: cityNewYork, lat: 40.7128, lng: -74.006, color: '#f6c28b' },
		{ name: cityLondon, lat: 51.5072, lng: -0.1276, color: '#9fd4c5' },
		{ name: cityTokyo, lat: 35.6762, lng: 139.6503, color: '#9fd4c5' },
		{ lat: 43.6532, lng: -79.3832, color: '#74bba8' },
		{ lat: 37.7749, lng: -122.4194, color: '#74bba8' },
		{ lat: -23.5505, lng: -46.6333, color: '#f6c28b' },
		{ lat: -34.6037, lng: -58.3816, color: '#74bba8' },
		{ lat: 48.8566, lng: 2.3522, color: '#9fd4c5' },
		{ lat: 50.1109, lng: 8.6821, color: '#74bba8' },
		{ lat: -26.2041, lng: 28.0473, color: '#74bba8' },
		{ lat: 25.2048, lng: 55.2708, color: '#f6c28b' },
		{ lat: 19.076, lng: 72.8777, color: '#74bba8' },
		{ lat: 1.3521, lng: 103.8198, color: '#74bba8' },
		{ lat: 37.5665, lng: 126.978, color: '#f6c28b' },
		{ lat: -33.8688, lng: 151.2093, color: '#74bba8' },
	]

	let seed = 20261011
	const random = () => {
		seed = (seed * 1664525 + 1013904223) >>> 0
		return seed / 4294967296
	}

	const arcs = Array.from({ length: 48 }, (_, index) => {
		const startIndex = Math.floor(random() * hubs.length)
		let endIndex = Math.floor(random() * hubs.length)

		if (endIndex === startIndex) {
			endIndex = (endIndex + 1) % hubs.length
		}

		const start = hubs[startIndex]
		const end = hubs[endIndex]

		if (!start || !end) {
			throw new Error('A global route needs two market hubs')
		}

		return {
			startLat: start.lat,
			startLng: start.lng,
			endLat: end.lat,
			endLng: end.lng,
			altitude: 0.11 + random() * 0.2,
			stroke: 0.42 + random() * 0.35,
			dashLength: 0.28 + random() * 0.4,
			dashGap: 0.25 + random() * 0.7,
			duration: 2200 + Math.round(random() * 3200),
			color:
				index % 4 === 0
					? ['rgba(255,142,83,0.96)', 'rgba(246,194,139,0.72)']
					: ['rgba(112,205,182,0.88)', 'rgba(159,212,197,0.68)'],
		}
	})

	const points = hubs.map(({ lat, lng, color }) => ({ lat, lng, color }))
	const labels = hubs.flatMap((hub) =>
		hub.name ? [{ lat: hub.lat, lng: hub.lng, name: hub.name }] : [],
	)

	return { arcs, labels, points }
}

export default function TradingGlobe(props: TradingGlobeProps) {
	const containerRef = useRef<HTMLDivElement>(null)
	const globeRef = useRef<GlobeHandle | undefined>(undefined)
	const globeMaterialRef = useRef<ShaderMaterial | null>(null)
	const postProcessingRef = useRef<ActivePostProcessing | null>(null)
	const [diameter, setDiameter] = useState(0)
	const [prefersReducedMotion, setPrefersReducedMotion] = useState(false)
	const [GlobeComponent, setGlobeComponent] = useState<GlobeComponentType | null>(null)
	const [globeMaterial, setGlobeMaterial] = useState<ShaderMaterial>()
	const { arcs, labels, points } = useMemo(
		() => createNetwork(props),
		[props.cityMexico, props.cityNewYork, props.cityLondon, props.cityTokyo],
	)

	const updateGlobeRotation = useCallback(({ lat, lng }: { lat: number; lng: number }) => {
		globeMaterialRef.current?.uniforms.globeRotation.value.set(lng, lat)
	}, [])

	useEffect(() => {
		const container = containerRef.current

		if (!container) {
			return
		}

		const observer = new ResizeObserver((entries) => {
			const entry = entries[0]

			if (!entry) {
				return
			}

			const nextDiameter = Math.min(Math.round(entry.contentRect.width), 520)
			setDiameter((currentDiameter) =>
				currentDiameter === nextDiameter ? currentDiameter : nextDiameter,
			)
		})

		observer.observe(container)

		return () => observer.disconnect()
	}, [])

	useEffect(() => {
		const preference = window.matchMedia('(prefers-reduced-motion: reduce)')
		const updateMotionPreference = () => setPrefersReducedMotion(preference.matches)

		updateMotionPreference()
		preference.addEventListener('change', updateMotionPreference)

		return () => preference.removeEventListener('change', updateMotionPreference)
	}, [])

	useEffect(() => {
		let isMounted = true

		import('react-globe.gl')
			.then((module) => {
				if (isMounted) {
					setGlobeComponent(() => module.default)
				}
			})
			.catch((error: unknown) => {
				console.error(GLOBE_IMPORT_ERROR, error)
			})

		return () => {
			isMounted = false
		}
	}, [])

	useEffect(() => {
		let isMounted = true
		const textureLoader = new TextureLoader().setCrossOrigin('anonymous')

		Promise.all([
			textureLoader.loadAsync(dayTextureUrl),
			textureLoader.loadAsync(nightTextureUrl),
		])
			.then(([dayTexture, nightTexture]) => {
				if (!isMounted) {
					dayTexture.dispose()
					nightTexture.dispose()
					return
				}

				dayTexture.colorSpace = SRGBColorSpace
				nightTexture.colorSpace = SRGBColorSpace

				const sun = getSunPosition(Date.now())
				const material = new ShaderMaterial({
					uniforms: {
						dayTexture: { value: dayTexture },
						nightTexture: { value: nightTexture },
						sunPosition: { value: new Vector2(sun.longitude, sun.latitude) },
						globeRotation: { value: new Vector2() },
					},
					vertexShader: dayNightShader.vertexShader,
					fragmentShader: dayNightShader.fragmentShader,
				})

				globeMaterialRef.current = material
				setGlobeMaterial(material)
			})
			.catch((error: unknown) => {
				console.error(EARTH_TEXTURE_LOAD_ERROR, error)
			})

		return () => {
			isMounted = false
			const material = globeMaterialRef.current

			if (material) {
				material.uniforms.dayTexture.value.dispose()
				material.uniforms.nightTexture.value.dispose()
				material.dispose()
				globeMaterialRef.current = null
			}
		}
	}, [])

	useEffect(() => {
		const material = globeMaterialRef.current

		if (!material) {
			return
		}

		let simulatedTime = Date.now()
		const updateSunPosition = () => {
			const sun = getSunPosition(simulatedTime)
			material.uniforms.sunPosition.value.set(sun.longitude, sun.latitude)
		}

		updateSunPosition()

		if (prefersReducedMotion) {
			return
		}

		let animationFrame = 0
		const advanceTime = () => {
			simulatedTime += simulatedMinutesPerFrame * 60_000
			updateSunPosition()
			animationFrame = requestAnimationFrame(advanceTime)
		}

		animationFrame = requestAnimationFrame(advanceTime)

		return () => cancelAnimationFrame(animationFrame)
	}, [globeMaterial, prefersReducedMotion])

	useEffect(() => {
		const globe = globeRef.current

		if (!globe || diameter === 0) {
			return
		}

		const initialView = { lat: 22, lng: -38, altitude: 1.9 }
		globe.pointOfView(initialView, 0)
		globeMaterialRef.current?.uniforms.globeRotation.value.set(initialView.lng, initialView.lat)
		const controls = globe.controls()
		controls.autoRotate = !prefersReducedMotion
		controls.autoRotateSpeed = prefersReducedMotion ? 0 : 0.65

		return () => {
			controls.autoRotate = false
		}
	}, [GlobeComponent, diameter, prefersReducedMotion])

	useEffect(() => {
		const globe = globeRef.current

		if (!globe || !GlobeComponent || diameter === 0) {
			return
		}

		let cancelled = false

		import('three/addons/postprocessing/RenderPixelatedPass.js')
			.then((pixelatedModule) => {
				const pixelatedPass = new pixelatedModule.RenderPixelatedPass(
					3,
					globe.scene(),
					globe.camera(),
					{ normalEdgeStrength: 0.14, depthEdgeStrength: 0.2 },
				)

				if (cancelled) {
					pixelatedPass.dispose()
					return
				}

				const composer = globe.postProcessingComposer()
				composer.addPass(pixelatedPass)
				postProcessingRef.current = { globe, composer, pixelatedPass }
			})
			.catch((error: unknown) => {
				console.error(POST_PROCESSING_INIT_ERROR, error)
			})

		return () => {
			cancelled = true
			const postProcessing = postProcessingRef.current

			if (postProcessing?.globe === globe) {
				postProcessing.composer.removePass(postProcessing.pixelatedPass)
				postProcessing.pixelatedPass.dispose()
				postProcessingRef.current = null
			}
		}
	}, [GlobeComponent, diameter])

	return (
		<div
			ref={containerRef}
			role='img'
			aria-label={props.label}
			className='relative mx-auto aspect-square w-full max-w-130 select-none'
		>
			<div aria-hidden='true' className='absolute inset-0'>
				{diameter > 0 && GlobeComponent ? (
					<GlobeComponent
						ref={globeRef}
						width={diameter}
						height={diameter}
						globeImageUrl={globeImageUrl}
						globeMaterial={globeMaterial}
						backgroundColor='rgba(0,0,0,0)'
						showGlobe={true}
						showAtmosphere={true}
						atmosphereColor='#71c8b1'
						atmosphereAltitude={0.16}
						showGraticules={false}
						globeCurvatureResolution={2}
						waitForGlobeReady={true}
						animateIn={false}
						arcsData={arcs}
						arcStartLat='startLat'
						arcStartLng='startLng'
						arcEndLat='endLat'
						arcEndLng='endLng'
						arcAltitude='altitude'
						arcStroke='stroke'
						arcColor='color'
						arcDashLength='dashLength'
						arcDashGap='dashGap'
						arcDashAnimateTime={prefersReducedMotion ? 0 : 'duration'}
						pointsData={points}
						pointLat='lat'
						pointLng='lng'
						pointColor='color'
						pointRadius={0.2}
						pointAltitude={0.025}
						pointLabel={() => ''}
						labelsData={labels}
						labelLat='lat'
						labelLng='lng'
						labelText='name'
						labelColor='rgba(239,247,247,0.92)'
						labelSize={0.62}
						labelAltitude={0.04}
						labelIncludeDot={true}
						labelDotRadius={0.17}
						onZoom={updateGlobeRotation}
					/>
				) : (
					<svg className='h-full w-full' viewBox='0 0 520 520' fill='none'>
						<defs>
							<radialGradient id='globe-fallback-fill' cx='0' cy='0' r='1' gradientTransform='translate(195 170) rotate(54) scale(340)'>
								<stop stopColor='#285b5b' />
								<stop offset='1' stopColor='#08131e' />
							</radialGradient>
							<linearGradient id='globe-fallback-route' x1='145' y1='302' x2='355' y2='212' gradientUnits='userSpaceOnUse'>
								<stop stopColor='#ff7b35' />
								<stop offset='1' stopColor='#f6c28b' />
							</linearGradient>
						</defs>
						<circle cx='260' cy='260' r='183' fill='url(#globe-fallback-fill)' stroke='#6da89a' strokeOpacity='.72' />
						<ellipse cx='260' cy='260' rx='183' ry='66' stroke='#91b6b2' strokeOpacity='.3' />
						<ellipse cx='260' cy='260' rx='100' ry='183' stroke='#91b6b2' strokeOpacity='.25' />
						<path d='M78 260h364M260 78v364' stroke='#91b6b2' strokeOpacity='.2' />
						<path d='M125 184l31-24 37-4 20 15 33 2 23 20-12 22-23 8-12 25-25 7-20-19-21-3-13-20-25-10z' fill='#39816c' />
						<path d='M232 266l22 11 16 24-7 24-17 27-9 32-16 23-11-29 2-25-14-25 8-25z' fill='#39816c' />
						<path d='M285 177l23-12 25 9 20 19 12 29-11 23-17 25-18 19-16-22-13-30-11-28z' fill='#39816c' />
						{
							fallbackRoutes.map((route, index) => (
								<path
									d={route}
									stroke={index % 4 === 0 ? 'url(#globe-fallback-route)' : '#71c8b1'}
									strokeOpacity={index % 4 === 0 ? 0.82 : 0.42}
									strokeWidth={index % 4 === 0 ? 1.7 : 1.1}
									strokeDasharray='4 7'
								/>
							))
						}
						<circle cx='145' cy='299' r='4' fill='#ff7b35' />
						<circle cx='351' cy='199' r='3.5' fill='#f6c28b' />
						<circle cx='392' cy='249' r='3' fill='#9fd4c5' />
						<circle cx='318' cy='301' r='3' fill='#9fd4c5' />
					</svg>
				)}
			</div>
		</div>
	)
}
