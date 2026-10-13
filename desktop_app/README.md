# Finance Scraper Desktop

Finance Scraper Desktop es una interfaz Electron/React para la API local de
`finance_scraper`. La aplicación inicia `finance-scraper api serve` antes de
mostrar el acceso y cierra el proceso de la API cuando termina la ventana. La
API usa loopback, un puerto disponible y un archivo PID del usuario; el proceso
no se expone a otros equipos de la red.

## Funciones

- Registro e inicio de sesión de perfiles locales, con reportes y watchlists
  aislados por `account_id`.
- Generación de reportes PDF, JSON, YAML y XLSX; los archivos se abren con la
  aplicación predeterminada de Windows (por ejemplo, Excel para `.xlsx` si el
  sistema lo tiene asociado).
- Conservación inicial de 15 días, configurable entre 10 minutos y 30 días.
- Gmail OAuth 2.0 por perfil, con el scope `gmail.send`; los reportes
  programados se envían al Gmail que autorizó cada persona y muestran
  `Finance Scraper` como nombre del remitente.
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
