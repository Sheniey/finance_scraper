# Finance Scraper API

## Ejecutar localmente

Desde la raíz del proyecto:

```powershell
.\.venv\Scripts\python.exe -m uvicorn api.main:app --reload
```

OpenAPI queda disponible en `http://127.0.0.1:8000/docs`.

La aplicación de escritorio inicia el mismo servicio con
`finance-scraper api serve --foreground --host 127.0.0.1 --port <puerto> --pid-file <archivo>`
y lo cierra con `finance-scraper api close` usando ese puerto y archivo PID.
Esas opciones son aditivas: el modo de CLI existente se conserva para usos
anteriores. El escritorio enlaza la API solo a loopback, usa una clave JWT
aleatoria protegida por Windows y guarda sus bases locales en `%APPDATA%`.

## Organización

```text
api/
├── core/          # configuración, base de datos, JWT, permisos y lifespan
├── exceptions/    # errores HTTP y respuestas JSON comunes
├── models/        # estado persistido de tokens y trabajos
├── repositories/  # adaptadores a los servicios financieros y SQLite de API
├── routers/       # endpoints HTTP
├── schemas/       # modelos de solicitud y respuesta
└── services/      # sesiones, rate limiting, colecciones y worker de reportes
```

La API reutiliza `finance.services.account` y
`finance.services.reporter.repository.generate_report`. El comando CLI
`Analyze` de `finance-cli.py` sirve como referencia de los argumentos de
generación; no se invoca desde el servidor porque ejecuta `asyncio.run`.

## Autenticación y permisos

`POST /auth/login` recibe JSON:

```json
{
  "email": "user@example.com",
  "password": "secret"
}
```

Devuelve `access_token` y `refresh_token`. El access token dura 15 minutos y el
refresh token 30 días por defecto. `POST /auth/refresh` recibe
`{"refresh_token": "..."}` y rota el refresh token; no se puede volver a usar el
token anterior. Las rutas protegidas esperan `Authorization: Bearer <access>`.
`POST /auth/logout` invalida los dos tokens de la sesión. Cambiar o eliminar la
cuenta invalida todas sus sesiones.

`POST /auth/register` crea un perfil de rol `user` para la aplicación de
escritorio. Requiere el token efímero `X-Finance-Desktop-Token` del proceso
local; no es un registro web público y no permite asignar roles.

Los JWT no se almacenan en texto claro. SQLite conserva el JTI, la sesión, el
tipo de token, su vencimiento y su estado de revocación; cada access token se
valida contra ese registro.

| Rutas | Permiso |
| --- | --- |
| `POST /auth/register` | Solo proceso local del escritorio |
| `POST /auth/login`, `POST /auth/refresh` | Públicas |
| `POST /auth/logout` | Sesión autenticada |
| `GET/POST /accounts`, `GET/PUT/DELETE /accounts/{uuid}` | Administrador |
| `GET/PUT/DELETE /accounts/me`, `POST /accounts/me/change-password` | Sesión autenticada |
| `/reports` y `/reports/{report_id}` | Sesión autenticada; los usuarios operan sobre sus reportes y los administradores pueden consultar/eliminar reportes globalmente |

Las operaciones globales de cuentas requieren el rol `admin`; usuarios normales
solo acceden a su propia cuenta. Los errores de autenticación y permisos usan
respuestas JSON con `error`, `message` y `status_code`. El rol administrador se
debe provisionar mediante un proceso administrativo confiable; el registro
local solo crea usuarios normales y nunca permite elevar el propio rol.

## Cuentas

- `GET /accounts` lista cuentas; `POST /accounts` crea una cuenta.
- `GET`, `PUT` y `DELETE /accounts/{uuid}` administran una cuenta por UUID.
- `GET /accounts/me` devuelve la cuenta autenticada.
- `PUT /accounts/me` actualiza nombre, idioma y watchlist de la propia cuenta.
- `DELETE /accounts/me` elimina la cuenta, sus sesiones y sus estados/artifacts
  de reportes.
- `POST /accounts/me/change-password` requiere `current_password` y
  `new_password`; al cambiarla revoca todas las sesiones.

## Reportes asíncronos

`POST /reports` y `POST /reports/me` aceptan los argumentos de `Analyze` que
aplican a una petición autenticada:

```json
{
  "ticker": "AAPL",
  "filename": "aapl.pdf",
  "explain": false,
  "mode": "custom",
  "charts": true,
  "ml_horizon": 15
}
```

`filename` es un nombre de archivo, no una ruta. Se permiten únicamente las
extensiones `.pdf`, `.json`, `.yaml`, `.txt` y `.xlsx`; la extensión selecciona
el renderer mediante `finance.renderers.smart_render_strategy`. El formato queda
fijado al crear el trabajo. La respuesta es
`202 Accepted` e incluye un ID `rep_<uuid>` y el estado inicial `PENDING`.

El worker, iniciado y detenido con el lifespan de FastAPI, persiste y procesa
trabajos en SQLite. Estados:

- `PENDING`: en cola.
- `IN_PROGRESS`: en generación.
- `COMPLETED`: artifact disponible.
- `FAILED`: error de generación; la respuesta de estado incluye un `error_code`.

`GET /reports/{report_id}` consulta el estado. El artifact solo se descarga con
`GET /reports/{report_id}/download` después de `COMPLETED`, usando el mismo
formato y nombre indicados al crear el trabajo. `POST /reports/run-watchlist` y
`POST /reports/me/run-watchlist` encolan un trabajo por cada elemento habilitado
de la watchlist actual.

Los JWT persisten en la base de estado de la API. La API y el CLI comparten el
almacén local de reportes: guarda el cache y los artifacts como BLOB con su
metadata. Cada artifact pertenece a su cuenta y se conserva 15 días por defecto;
`api.report_retention_seconds` admite de 600 segundos a 30 días; al reiniciar
la API, el nuevo plazo se aplica a los reportes completados existentes. En
`dev` no se purgan los reportes. Los trabajos pendientes y sus leases también
viven en ese store y se pueden recuperar tras un reinicio.
En el primer arranque, la API copia y verifica los reportes legacy antes de
eliminar sus archivos y tablas `api_report_jobs`; la tabla `api_tokens` se
conserva en la base de estado de la API.

El cache de Yahoo Finance dura 15 minutos; los análisis de acciones y los
resultados canónicos de reportes duran una hora. La clave del análisis incluye
idioma y estilo; la del reporte incluye ticker/región, preset y opciones
relevantes. Los resultados canónicos no guardan la cuenta. Si su saldo neto de
una acción/región es positivo, el reporte no se comparte por cache. Cada
solicitud genera su propio artifact BLOB, accesible sólo al dueño del `report_id`.
Los archivos de salida de `Analyze` y los PDF de `SendReport` se guardan en el
mismo store que usa la API.

## Gmail OAuth y reportes programados

La integración de escritorio autoriza una cuenta Google mediante el navegador
del sistema, `state` y PKCE. Solicita `gmail.send` y los scopes de identidad
`openid email`; no utiliza contraseña de aplicación, SMTP ni acceso de lectura
del correo. El encabezado visible es `Finance Scraper <correo-autorizado>` y
los reportes se envían al Gmail que autorizó el perfil.

Configura `GOOGLE_OAUTH_CLIENT_ID` con un OAuth Client de tipo Desktop después
de activar Gmail API. El refresh token se guarda en Windows Credential Manager,
vinculado al `account_id`; SQLite conserva solo correo, scopes y fechas. Antes
de distribuir el envío a cualquier usuario, el propietario debe completar el
consentimiento y la verificación que exija Google para Gmail.

`GET/POST /schedules/me` lista y crea horarios diarios; el usuario puede pausar
o eliminar los propios con `PATCH/DELETE /schedules/me/{schedule_id}`. Cada
horario conserva tickers, formato, hora y zona IANA local. El helper oculto del
escritorio activa la API solo durante un envío programado. El Programador de
tareas de Windows usa la sesión interactiva, recupera ejecuciones vencidas al
volver y no necesita la contraseña de Windows. Los perfiles de Finance Scraper
y sus autorizaciones de Gmail permanecen separados.

El worker limita el paralelismo según núcleos lógicos y memoria disponible,
respetando `api.report_worker_max_concurrency` (por defecto 4, máximo 16).
Los reportes XLSX incluyen hojas de resumen y datos; el texto potencialmente
interpretable como fórmula se escapa antes de escribirlo.

## Colecciones

`GET /accounts` y `GET /reports` aceptan:

- `page` (desde 1) y `page_size` (por defecto 20; máximo 100), o un
  `page_cursor` opaco; no se combinan `page` y `page_cursor`.
- `fields`: nombres separados por coma y limitados a los campos de salida.
- `sort`: campos permitidos separados por coma; prefijo `-` para descendente.
- `filter`: objeto JSON URL-encoded de coincidencias exactas sobre campos
  permitidos, por ejemplo `filter={"status":"COMPLETED"}`.

Los nombres de campo de `fields`, `sort` y `filter` se validan mediante
allowlists; no se aceptan expresiones SQL.

## Rate limiting y configuración

Los límites están en el modelo tipado de `api/core/config.py` y se configuran en
`api/env.yaml`:

- Login: 5 intentos por minuto e IP.
- Registro local de escritorio: 3 intentos por minuto e IP.
- Generación de reportes: 3 solicitudes por minuto y cuenta.
- Demás endpoints: 60 solicitudes por minuto y cuenta (o IP antes de autenticar).

El almacenamiento predeterminado del limitador es memoria local al proceso; un
despliegue multiproceso que necesite cuotas compartidas debe configurar un
backend compartido. En producción también se debe configurar `JWT_SECRET_KEY`
en el entorno; no se debe usar la clave de desarrollo predeterminada.

Las rutas están declaradas directamente en los routers; `api/env.yaml` contiene
configuración de la API, no plantillas de paths.
