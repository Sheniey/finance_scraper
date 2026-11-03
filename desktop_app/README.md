
<div align="center">
<a name="readme-top"></a>

<a href="https://www.financescraper.com/" target="_blank" rel="noopener noreferrer">
  <img src="https://raw.githubusercontent.com/sheniey/finance_scraper/refs/heads/main/website/public/icons/fs_banner_dark_px.png" alt="Logo" width="800" />
</a>

<br>

[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]

</div>

<br>
<br>
<br>

Finance Scraper is a tool for generating **financial reports** and insights from various data sources with colorful feedbacks, deep analysis, AI explanations, and customizable report formats. Finance Scraper offers a local-first, synchronization source database, privacy-focused, user-friendly, concurrent, extensible, customizable and robust tool for managing and analyzing financial data.

<br>

## 🗂️ Desktop Application Section

This project folder contains the official Finance Scraper desktop application.

The localized Home page is served at `/{locale}/home`. Visiting `/` selects a supported browser language (falling back to English), and `/{locale}` redirects to that locale's Home page.

The website is built with Astro.js and Tailwind CSS and is responsible for:
- Shared, localized site navigation
- Executable downloads
- Documentation access
- SEO optimization
- Internationalization
- Product information
- Contact information
- Legal information

<p align="right">
    <strong><a href="#readme-top">↑ To Top ↑</a></strong>
</p>

---

## 🚀 Getting Started
The step by step guide to launch the website locally.

> [!IMPORTANT]
> Make sure you have `pnpm` installed globally before proceeding. You can install it using `npm install -g pnpm`.

1. Clone the repository and navigate to the website folder:
```bash
git clone https://github.com/sheniey/finance_scraper.git
cd finance_scraper/website
```

2. Install the dependencies:
```bash
pnpm install
```

3. Start the local development server:
```bash
pnpm dev
```

> [!NOTE]
> To build the production site, use `pnpm build` instead of `pnpm dev`.

4. Go to your browser and open `http://localhost:4321`:

<br>

| Command | Action  |
|---------|---------|
| `pnpm install` | Installs dependencies  |
| `pnpm dev` | Starts local dev server at `localhost:4321` |
| `pnpm build` | Build your production site to `./dist/` |
| `pnpm preview` | Preview your build locally, before deploying |
| `pnpm astro ...` | Run CLI commands like `astro add`, `astro check` |
| `pnpm astro -- --help` | Get help using the Astro CLI |

<p align="right">
    <strong><a href="#readme-top">↑ To Top ↑</a></strong>
</p>

---

## 🚀 Contributing
We welcome contributions from the community. If you would like to contribute, please follow these steps:

> [!IMPORTANT]
> When contributing, make sure to modify **only the `website` section** of the repository. Changes to other sections are outside the scope of this contribution process.

1. Make a **Fork** of this repository.

2. Create a new branch for your feature or bugfix:
```bash
git switch -c {prefix}/{branch_name}
```
Alternatively, you can use `git checkout -b` (Git >= 2.23 is recommended for git switch).

**We recommend following the naming convention for branch names:**

| Prefix | Purpose |
|---------|---------|
| feat/ | New feature |
| fix/ | Bug fix |
| docs/ | Documentation |
| test/ | Tests |
| refactor/ | Refactoring |
| chore/ | Maintenance |
| style/ | Formatting and styling |

**Example:**
- `feat/responsive-navbar`
- `fix/mobile-layout`
- `docs/update-installation-guide`

3. Add your changes to your Fork and commit them:
```bash
git add .
git commit -m "{prefix}: <description>"
```
Use the same prefix for your commit message as your branch name.

4. Push your changes to your branch:
```bash
git push origin {prefix}/{branch_name}
```

> [!WARNING]
> This command must receive the name of your branch and your implementation exactly as defined in step two.

5. Open a Pull Request against the original repository's appropriate branch. Include a clear description of your changes and their purpose.

### ⚠️ Before submitting

Make sure that:
- Your changes are limited to the website section.
- Your branch follows the recommended naming convention.
- Your commit messages use the appropriate prefix. You can add a scope in parentheses after the prefix if needed.
- Your Pull Request clearly describes your implementation.

<p align="right">
    <strong><a href="#readme-top">↑ To Top ↑</a></strong>
</p>

---

<br>
<br>
<br>

<div align="center">

**Thanks to all the collaborators for their precious contribution!**

[![Contributors](https://contrib.rocks/image?repo=sheniey/finance_scraper&max=500&columns=20)](https://github.com/sheniey/finance_scraper/graphs/contributors)

</div>


<!-- Repository Links -->
[contributors-shield]: https://img.shields.io/github/contributors/sheniey/finance_scraper.svg?style=for-the-badge
[contributors-url]: https://github.com/sheniey/finance_scraper/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/sheniey/finance_scraper.svg?style=for-the-badge
[forks-url]: https://github.com/sheniey/finance_scraper/network/members
[stars-shield]: https://img.shields.io/github/stars/sheniey/finance_scraper.svg?style=for-the-badge
[stars-url]: https://github.com/sheniey/finance_scraper/stargazers
[issues-shield]: https://img.shields.io/github/issues/sheniey/finance_scraper.svg?style=for-the-badge
[issues-url]: https://github.com/sheniey/finance_scraper/issues
<!-- Repository Links -->



# Finance Scraper Desktop

Finance Scraper Desktop es una interfaz Electron/React para la API local de
`finance_scraper`. La aplicación inicia `finance-scraper api serve` antes de
mostrar el acceso y cierra el proceso de la API cuando termina la ventana. La
API usa loopback, un puerto disponible y un archivo PID del usuario; el proceso
no se expone a otros equipos de la red.

## Funciones

- Registro e inicio de sesión de perfiles locales, con reportes y watchlists
  aislados por `account_id`.
- La sección **Reportes** muestra el historial, permite exportar archivos y
  abre un modal para generar reportes. El modo personalizado permite ordenar
  las secciones y guarda esa preferencia en `account_custom_reports`.
- **Portafolio** registra compras y ventas por ticker, mercado, precio y fecha.
  La posición neta del perfil se incorpora al contexto de las explicaciones de
  IA.
- Generación de reportes PDF, JSON, YAML y XLSX; los archivos se abren con la
  aplicación predeterminada de Windows (por ejemplo, Excel para `.xlsx` si el
  sistema lo tiene asociado).
- Conservación inicial de 15 días, configurable entre 10 minutos y 30 días.
- El inicio de sesión de Finance Scraper usa exclusivamente cuentas locales.
  Google se conecta desde **Programaciones** y solo para autorizar envíos Gmail
  con el scope `gmail.send`; el remitente usa el nombre del perfil y el Gmail
  que cada persona autorizó.
- **Proveedores de IA** separa las claves de API de las preferencias. Las
  claves OpenAI, DeepSeek y Anthropic se guardan en el `.env` local de datos de
  la aplicación y están disponibles para todos sus perfiles. Ollama se detecta
  localmente; la instalación solo se inicia después de que la persona la acepte.
- Horarios diarios ejecutados por un helper oculto y el Programador de tareas
  de Windows. Cerrar sesión en Finance Scraper no detiene los horarios. Debe
  permanecer iniciada la sesión de Windows; las tareas atrasadas se recuperan
  al volver.
- Worker con concurrencia acotada automáticamente por CPU/memoria y por el
  máximo elegido en Configuración.
- Interfaz localizada en español e inglés, con español como fallback.

## Desarrollo

Desde `desktop_app/`:

```powershell
pnpm install
pnpm dev
pnpm run typecheck
pnpm run build:ui
```

`pnpm dev` compila el preload TypeScript a CommonJS antes de abrir Electron,
porque el preload aislado no puede ejecutar módulos ESM.

## Publicación de OAuth Gmail

La aplicación debe distribuirse con un OAuth Client de Google de tipo Desktop
configurado por quien publica el producto. En desarrollo, `GOOGLE_OAUTH_CLIENT_ID`
puede venir del entorno o del `.env` del backend; las personas usuarias no
introducen este identificador ni una API key de Google. La autorización Gmail
se completa en el navegador del sistema, ya que Google no permite el login OAuth
de escritorio dentro de un iframe embebido. El comando `pnpm build` incorpora
el identificador público del entorno de compilación al paquete de escritorio.

`pnpm dev` inicia Vite y Electron. En desarrollo, el proceso local de Finance
Scraper se ejecuta con el Python virtual del repositorio y `finance-cli.py`.

## Empaquetado

Primero reconstruye el CLI/API para que el instalador incluya los cambios
actuales de autenticación, OAuth, reportes y worker. Desde `finance_scraper/`:

```powershell
uv sync --group build
uv run --group build python -m PyInstaller --noconfirm --clean finance-cli.spec
```

Después, desde `desktop_app/`:

```powershell
pnpm build
```

El paquete de Electron incluye `finance_scraper/dist/finance-scraper/` como
recurso `finance-scraper`. Si el ejecutable se instala en otra ubicación,
Configuración permite seleccionar `finance-scraper.exe`. El instalador
independiente del CLI, `finance_scraper/installer.iss`, puede añadir su carpeta
al `PATH` del usuario actual para ejecutarlo desde una terminal.

## Datos y secretos

Los datos de escritorio se guardan en `%APPDATA%\Finance Scraper`; el API
configura por separado su SQLite de cuentas, estado y artifacts. El modo
desktop no carga el `.env` del desarrollador completo ni habilita sincronización
remota. Desde Ajustes > Conexiones puedes guardar claves de OpenAI, DeepSeek y
Anthropic en un `.env` junto al ejecutable de Finance Scraper; únicamente esas
claves se pasan al API local y los perfiles de esta instalación comparten esa
configuración. El `.env` contiene estas claves en texto plano; protege la
carpeta y no compartas el archivo.
El secreto JWT y el token de control de la API se guardan cifrados con el
almacén seguro de Windows; los tokens de sesión permanecen en memoria de
Electron y nunca se escriben en `localStorage`.

Los refresh tokens de Gmail se guardan en Windows Credential Manager y se
nombran por perfil local. SQLite conserva solamente correo, scopes y fechas.
El acceso con Google usa el correo verificado por OAuth; el acceso de Gmail para
envíos programados sigue siendo una conexión independiente. La contraseña de
aplicación SMTP no se usa en la interfaz.
La separación evita que otro perfil de Finance Scraper vea reportes dentro de
la aplicación; quien tenga acceso al mismo usuario de Windows puede leer los
archivos locales de ese usuario.

## Requisito manual para Gmail

Antes de habilitar envíos a usuarios públicos, el propietario debe:

1. Crear un proyecto de Google Cloud y activar Gmail API.
2. Configurar la pantalla de consentimiento OAuth y un cliente OAuth de tipo
   **Desktop app**.
3. Configurar el `client_id` en Finance Scraper Desktop.
4. Completar las pruebas/consentimiento y la verificación que Google exija para
   el scope `gmail.send`.

El Client ID es público y no es una contraseña. No se necesita ni se debe
distribuir un `client_secret` o una contraseña de aplicación. Hasta completar
la configuración de Google, la app puede iniciar sesión, crear reportes y
mostrar la conexión Gmail como no configurada; los envíos no se simulan como
exitosos.
