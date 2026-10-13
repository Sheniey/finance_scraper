# reportlab-python

Skill para GitHub Copilot especializada en ReportLab para Python.

## Instalación como skill de proyecto

Copia esta carpeta a:

```text
.github/skills/reportlab-python/
```

Debe quedar:

```text
.github/
└── skills/
    └── reportlab-python/
        └── SKILL.md
```

Copilot detectará la skill por su `SKILL.md` y decidirá cuándo usarla según el `description`. También puedes solicitarla explícitamente con:

```text
Usa la /reportlab-python skill para crear este PDF...
```

## Instalación personal

También puede colocarse en:

```text
~/.copilot/skills/reportlab-python/SKILL.md
```

o:

```text
~/.agents/skills/reportlab-python/SKILL.md
```

## Actualización de contexto en Copilot CLI

Si ya tienes una sesión abierta:

```text
/skills reload
```

Para comprobarla:

```text
/skills info reportlab-python
```

## Nota

La skill contiene instrucciones y patrones de ingeniería; no instala ReportLab. El proyecto debe instalar la dependencia Python:

```bash
python -m pip install reportlab
```
