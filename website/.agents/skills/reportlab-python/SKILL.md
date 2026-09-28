---
name: reportlab-python
description: Especialista en ReportLab para Python. Usa esta skill cuando la tarea implique crear, modificar, depurar, revisar, optimizar o diseñar PDFs con ReportLab, incluyendo pdfgen Canvas, Platypus, tablas, estilos, fuentes, imágenes, gráficos vectoriales, numeración de páginas, índices, documentos multipágina, plantillas, formularios, metadatos, enlaces, generación masiva de PDFs y diagnóstico de errores de layout.
---

# Skill: ReportLab para Python

## 0. Misión

Actúa como un ingeniero senior especializado en generación de PDF con ReportLab en Python.

Tu objetivo es producir PDFs:
- correctos técnicamente;
- visualmente profesionales;
- mantenibles;
- reproducibles;
- robustos ante contenido variable;
- compatibles con las versiones modernas de ReportLab;
- fáciles de probar y depurar.

No te limites a "hacer que genere un PDF". Debes pensar en:
1. arquitectura del documento;
2. flujo y paginación;
3. tipografía;
4. tablas;
5. imágenes;
6. separación entre datos, estilos y layout;
7. accesibilidad cuando sea viable;
8. rendimiento;
9. validación del PDF generado;
10. mantenibilidad del código.

Cuando exista una decisión entre `pdfgen.canvas` y Platypus, elige conscientemente la herramienta adecuada y explica brevemente la razón si la decisión no es obvia.

---

# 1. Regla de decisión: Canvas vs Platypus

## Usa `pdfgen.canvas` cuando:
- el documento tiene coordenadas y posiciones completamente controladas;
- se dibujan etiquetas, tickets, tarjetas, recibos o formularios;
- el contenido es corto y de geometría conocida;
- se necesita dibujo directo de líneas, rectángulos, círculos, paths o texto;
- el diseño es más parecido a "dibujar una página" que a componer un documento fluido.

Ejemplo:

```python
from reportlab.pdfgen import canvas

c = canvas.Canvas("salida.pdf")
c.setFont("Helvetica", 12)
c.drawString(72, 720, "Hola ReportLab")
c.showPage()
c.save()
```

## Usa Platypus cuando:
- el documento puede tener muchas páginas;
- el texto debe fluir;
- hay tablas;
- los títulos y párrafos pueden cambiar de tamaño;
- hay listas, imágenes, saltos de página o contenido variable;
- se necesitan encabezados/pies repetidos;
- se necesita una tabla de contenidos;
- se necesitan múltiples layouts o `PageTemplate`.

Arquitectura típica:

```text
DocTemplate
   └── PageTemplate
       └── Frame
           └── Flowables
               ├── Paragraph
               ├── Table
               ├── Image
               ├── Spacer
               ├── PageBreak
               └── Flowable personalizado
```

## Regla práctica

Si el usuario dice "informe", "reporte", "factura multipágina", "contrato", "catálogo", "manual", "estado de cuenta" o "PDF con tablas", empieza evaluando Platypus.

Si dice "ticket", "etiqueta", "credencial", "plantilla exacta", "coordenadas", "dibujar", empieza evaluando Canvas.

Se puede combinar ambos enfoques. Por ejemplo, Platypus para el flujo principal y Canvas en `onPage` para encabezados, fondos, marcas de agua y pies.

---

# 2. Instalación y entorno

Preferir un entorno virtual.

```bash
python -m venv .venv
```

Activación:

```bash
# Linux/macOS
source .venv/bin/activate

# Windows PowerShell
.venv\Scripts\Activate.ps1
```

Instalación:

```bash
python -m pip install reportlab
```

Para bitmap/rendering opcional en instalaciones modernas puede ser necesario instalar extras apropiados según el caso:

```bash
python -m pip install "reportlab[pycairo]"
```

No asumas que una API pertenece a la versión instalada. Si el proyecto fija una versión de ReportLab, respétala.

Antes de implementar una solución grande, comprueba:

```bash
python -c "import reportlab; print(reportlab.Version)"
```

Buenas prácticas:
- fijar versión en `requirements.txt` o `pyproject.toml` cuando la reproducibilidad sea importante;
- no mezclar APIs antiguas y modernas sin necesidad;
- probar el PDF realmente generado, no solo comprobar que el script termina sin excepción.

---

# 3. Imports frecuentes

## Canvas

```python
from reportlab.pdfgen import canvas
```

## Platypus

```python
from reportlab.platypus import (
    SimpleDocTemplate,
    BaseDocTemplate,
    PageTemplate,
    Frame,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
    PageBreak,
    KeepTogether,
    KeepInFrame,
    NextPageTemplate,
)
```

Otros útiles:

```python
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.lib.pagesizes import A4, LETTER, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, cm, inch
```

Fuentes:

```python
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase.pdfmetrics import registerFontFamily
```

Imágenes:

```python
from reportlab.lib.utils import ImageReader
```

Gráficos:

```python
from reportlab.graphics.shapes import Drawing, Rect, String, Line
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics import renderPDF
```

---

# 4. Sistema de coordenadas

ReportLab utiliza normalmente puntos (`points`) como unidad.

```text
1 inch = 72 pt
1 inch = 25.4 mm
```

Usa las constantes:

```python
from reportlab.lib.units import mm, cm, inch

margen = 20 * mm
```

En Canvas:
- origen `(0, 0)` abajo a la izquierda;
- `x` crece hacia la derecha;
- `y` crece hacia arriba.

Ejemplo:

```python
width, height = A4

c.drawString(20 * mm, height - 20 * mm, "Título")
```

Evita números mágicos como `56`, `81`, `734`. Prefiere:

```python
LEFT = 20 * mm
TOP = 25 * mm
```

---

# 5. Tamaños de página y orientación

```python
from reportlab.lib.pagesizes import A4, LETTER, landscape

doc = SimpleDocTemplate(
    "salida.pdf",
    pagesize=A4,
)
```

Horizontal:

```python
doc = SimpleDocTemplate(
    "salida.pdf",
    pagesize=landscape(A4),
)
```

Para conocer dimensiones:

```python
width, height = A4
```

No hardcodees dimensiones si el documento debe admitir diferentes tamaños.

---

# 6. Canvas: API fundamental

Ejemplo base:

```python
from reportlab.pdfgen import canvas

def crear_pdf(path: str) -> None:
    c = canvas.Canvas(path, pagesize=A4)

    width, height = A4

    c.setTitle("Mi PDF")
    c.setAuthor("Mi aplicación")

    c.setFont("Helvetica-Bold", 18)
    c.drawString(20 * mm, height - 20 * mm, "Título")

    c.setFont("Helvetica", 10)
    c.drawString(20 * mm, height - 30 * mm, "Contenido")

    c.showPage()
    c.save()
```

## Estado gráfico

Usa:

```python
c.saveState()
# modificaciones
c.restoreState()
```

Especialmente en funciones reutilizables:

```python
def dibujar_marca_agua(c, width, height):
    c.saveState()
    # ...
    c.restoreState()
```

Nunca dejes cambios globales de estado sin restaurar en helpers complejos.

## Transformaciones

```python
c.translate(x, y)
c.rotate(45)
c.scale(0.5, 0.5)
```

Para rotaciones o transformaciones locales:

```python
c.saveState()
c.translate(...)
c.rotate(...)
c.drawString(...)
c.restoreState()
```

## Líneas y formas

```python
c.line(x1, y1, x2, y2)
c.rect(x, y, width, height)
c.roundRect(x, y, width, height, radius)
c.circle(x, y, radius)
c.ellipse(x1, y1, x2, y2)
```

Para paths:

```python
p = c.beginPath()
p.moveTo(...)
p.lineTo(...)
p.curveTo(...)
p.close()
c.drawPath(p, stroke=1, fill=0)
```

## Color

```python
from reportlab.lib import colors

c.setFillColor(colors.HexColor("#1F2937"))
c.setStrokeColor(colors.HexColor("#D1D5DB"))
```

No uses colores hardcodeados por todo el proyecto. Centralízalos.

---

# 7. Texto con Canvas

Texto simple:

```python
c.drawString(x, y, texto)
```

Centrado:

```python
c.drawCentredString(x, y, texto)
```

Alineado a la derecha:

```python
c.drawRightString(x, y, texto)
```

Para textos largos, no uses `drawString` esperando wrapping automático. Usa Platypus `Paragraph`, o calcula manualmente el wrapping.

## TextObject

Para bloques de texto controlados:

```python
text = c.beginText()
text.setTextOrigin(20 * mm, 250 * mm)
text.setFont("Helvetica", 10)
text.setLeading(14)

for linea in lineas:
    text.textLine(linea)

c.drawText(text)
```

---

# 8. Platypus: arquitectura correcta

Platypus separa:
- documento;
- plantilla de página;
- frames;
- flowables;
- estilos;
- contenido.

Ejemplo mínimo:

```python
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm

styles = getSampleStyleSheet()

doc = SimpleDocTemplate(
    "salida.pdf",
    pagesize=A4,
    leftMargin=20 * mm,
    rightMargin=20 * mm,
    topMargin=20 * mm,
    bottomMargin=20 * mm,
)

story = [
    Paragraph("Título", styles["Title"]),
    Spacer(1, 8 * mm),
    Paragraph("Contenido del documento.", styles["BodyText"]),
]

doc.build(story)
```

---

# 9. `SimpleDocTemplate` vs `BaseDocTemplate`

## `SimpleDocTemplate`

Usarlo para:
- documentos convencionales;
- una sola plantilla de página;
- encabezado y pie sencillos.

```python
doc = SimpleDocTemplate(...)
doc.build(
    story,
    onFirstPage=draw_first_page,
    onLaterPages=draw_later_pages,
)
```

## `BaseDocTemplate`

Usarlo cuando:
- hay múltiples frames;
- hay columnas;
- hay varias plantillas;
- cambia el layout entre páginas;
- se necesita control fino del ciclo de paginación.

Ejemplo conceptual:

```python
class MyDocTemplate(BaseDocTemplate):
    pass
```

y:

```python
frame = Frame(
    left,
    bottom,
    width,
    height,
    id="normal",
)

template = PageTemplate(
    id="normal",
    frames=[frame],
    onPage=draw_page,
)

doc = MyDocTemplate("salida.pdf")
doc.addPageTemplates([template])
```

---

# 10. Frames y columnas

Un `Frame` define el área donde fluyen los `Flowable`.

```python
frame = Frame(
    x,
    y,
    width,
    height,
    leftPadding=6,
    rightPadding=6,
    topPadding=6,
    bottomPadding=6,
    id="columna",
)
```

Para dos columnas:

```python
frames = [
    Frame(..., id="left"),
    Frame(..., id="right"),
]
```

El orden de los frames afecta al flujo. Diseña explícitamente cómo debe pasar el contenido de una columna a otra.

---

# 11. Styles: no formatees texto manualmente por todo el código

Centraliza estilos:

```python
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT

body = ParagraphStyle(
    "Body",
    fontName="Helvetica",
    fontSize=9.5,
    leading=13,
    alignment=TA_LEFT,
    spaceAfter=6,
)
```

Ejemplo de sistema de estilos:

```python
styles = {
    "title": ParagraphStyle(...),
    "subtitle": ParagraphStyle(...),
    "heading1": ParagraphStyle(...),
    "heading2": ParagraphStyle(...),
    "body": ParagraphStyle(...),
    "small": ParagraphStyle(...),
    "table_header": ParagraphStyle(...),
    "table_body": ParagraphStyle(...),
}
```

Reglas:
- nombres semánticos;
- evita copiar estilos casi idénticos;
- define `leading`;
- controla `spaceBefore`/`spaceAfter`;
- define `keepWithNext` para encabezados cuando proceda.

---

# 12. Paragraph

`Paragraph` es el flowable principal para texto con wrapping.

```python
p = Paragraph(
    "Texto <b>negrita</b> y <i>cursiva</i>.",
    styles["body"],
)
```

Markup frecuente:
- `<b>...</b>`
- `<i>...</i>`
- `<u>...</u>`
- `<br/>`
- `<super>...</super>`
- `<sub>...</sub>`
- `<font ...>...</font>`

Ejemplo:

```python
Paragraph(
    'Precio: <b>$125.00</b><br/>'
    '<font color="#666666">IVA incluido</font>',
    styles["body"],
)
```

No metas HTML arbitrario. El parser de Paragraph usa un subconjunto específico de markup.

## Escape de contenido dinámico

Si el texto proviene de usuario, base de datos o API, no insertes directamente caracteres que puedan interpretarse como markup.

Usa:

```python
from xml.sax.saxutils import escape

texto_seguro = escape(texto)
```

Después, si necesitas markup controlado, compón cuidadosamente el contenido.

---

# 13. Tablas

Import:

```python
from reportlab.platypus import Table, TableStyle
```

Tabla básica:

```python
data = [
    ["Producto", "Cantidad", "Precio"],
    ["A", "2", "$10.00"],
    ["B", "1", "$20.00"],
]

table = Table(
    data,
    colWidths=[80 * mm, 30 * mm, 40 * mm],
)
```

Estilo:

```python
table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F2937")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#D1D5DB")),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("LEFTPADDING", (0, 0), (-1, -1), 6),
    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
]))
```

## Tablas profesionales

Para texto largo, usa `Paragraph` dentro de las celdas:

```python
data = [
    [
        Paragraph("<b>Descripción</b>", styles["table_header"]),
        Paragraph("<b>Importe</b>", styles["table_header"]),
    ],
    [
        Paragraph(escape(descripcion), styles["table_body"]),
        Paragraph("$100.00", styles["table_body"]),
    ],
]
```

No confíes en strings largos dentro de celdas si necesitas wrapping controlado.

## Repetir encabezados

```python
Table(
    data,
    colWidths=[...],
    repeatRows=1,
)
```

## Dividir tablas entre páginas

Las tablas pueden dividirse entre páginas. Para documentos largos, considera `LongTable` cuando sea apropiado:

```python
from reportlab.platypus import LongTable
```

## Spans

```python
("SPAN", (0, 0), (2, 0))
```

Usa spans solo cuando aporten estructura real. Las tablas con demasiados spans son más difíciles de mantener y pueden complicar la paginación.

---

# 14. Tablas robustas ante datos variables

Siempre considera:
- textos muy largos;
- celdas vacías;
- números grandes;
- muchas filas;
- páginas con diferentes alturas disponibles;
- encabezados repetidos;
- filas que no deben partirse cuando sea posible.

Si el contenido es variable:
1. define anchos de columna;
2. usa `Paragraph` para texto;
3. deja que las alturas se calculen cuando sea razonable;
4. prueba con datos mínimos, normales y extremos.

---

# 15. Imágenes

Con Platypus:

```python
from reportlab.platypus import Image

img = Image("logo.png")
img.drawWidth = 40 * mm
img.drawHeight = 20 * mm
```

Preservar proporción:

```python
from PIL import Image as PILImage

with PILImage.open("logo.png") as im:
    w, h = im.size

target_w = 40 * mm
target_h = target_w * h / w
```

No dejes imágenes gigantes sin necesidad. Redimensiona o controla sus dimensiones.

Para Canvas:

```python
c.drawImage(
    "logo.png",
    x,
    y,
    width=40 * mm,
    height=20 * mm,
    preserveAspectRatio=True,
    mask="auto",
)
```

---

# 16. Fuentes y Unicode

No asumas que Helvetica/Times/Courier cubren todos los caracteres Unicode.

Para español básico, símbolos y alfabetos adicionales, considera una fuente TrueType/OpenType apropiada.

Registro TTF:

```python
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

pdfmetrics.registerFont(
    TTFont("MiFuente", "fonts/MiFuente.ttf")
)
```

Para familias:

```python
from reportlab.pdfbase.pdfmetrics import registerFontFamily

registerFontFamily(
    "MiFamilia",
    normal="MiFuente",
    bold="MiFuente-Bold",
    italic="MiFuente-Italic",
    boldItalic="MiFuente-BoldItalic",
)
```

Luego:

```python
style = ParagraphStyle(
    "Body",
    fontName="MiFuente",
    fontSize=10,
    leading=14,
)
```

Buenas prácticas:
- incluye las fuentes necesarias de forma legal;
- usa rutas robustas;
- registra fuentes una sola vez;
- evita depender de rutas relativas al directorio actual si el programa puede ejecutarse desde distintos lugares.

Patrón:

```python
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
FONT_DIR = BASE_DIR / "fonts"
```

---

# 17. Encabezados y pies de página

Con `SimpleDocTemplate`:

```python
def draw_page(canvas, doc):
    canvas.saveState()

    width, height = A4

    canvas.setFont("Helvetica", 8)
    canvas.drawString(
        20 * mm,
        10 * mm,
        "Mi empresa",
    )

    canvas.drawRightString(
        width - 20 * mm,
        10 * mm,
        f"Página {doc.page}",
    )

    canvas.restoreState()
```

Y:

```python
doc.build(
    story,
    onFirstPage=draw_page,
    onLaterPages=draw_page,
)
```

No pongas encabezados/pies como `Paragraph` normales si deben estar fijos respecto a la página.

---

# 18. Primera página diferente

Patrón:

```python
def draw_first_page(canvas, doc):
    canvas.saveState()
    # portada / header especial
    canvas.restoreState()

def draw_later_pages(canvas, doc):
    canvas.saveState()
    # header/pie normal
    canvas.restoreState()

doc.build(
    story,
    onFirstPage=draw_first_page,
    onLaterPages=draw_later_pages,
)
```

---

# 19. Número total de páginas

Si el documento necesita "Página X de Y", una estrategia habitual es hacer una primera pasada para capturar páginas o usar una clase de canvas que guarde estados y luego renderizar el total.

No improvises una segunda pasada si el documento contiene contenido no determinista.

La solución debe conservar:
- posiciones;
- estado gráfico;
- metadatos;
- enlaces;
- bookmarks;
- compresión;
- orden de páginas.

Si se implementa un `NumberedCanvas`, encapsúlalo y pruébalo con:
- 1 página;
- 2 páginas;
- muchas páginas.

---

# 20. Saltos y control del flujo

Flowables útiles:

```python
Spacer(1, 8 * mm)
PageBreak()
```

Para mantener contenido junto:

```python
KeepTogether([
    Paragraph("Título", styles["heading2"]),
    Paragraph("Texto asociado...", styles["body"]),
])
```

Para controlar bloques que deben ocupar un área:

```python
KeepInFrame(...)
```

No uses `PageBreak` como parche para arreglar un problema de layout que debería resolverse con estilos, tamaños o flowables.

---

# 21. `keepWithNext`

Para evitar que un título quede solo al final de una página:

```python
heading = ParagraphStyle(
    "Heading",
    parent=styles["Heading2"],
    keepWithNext=True,
)
```

Úsalo en títulos y subtítulos cuando tenga sentido.

---

# 22. Índice / Table of Contents

Para documentos largos:
- usa `TableOfContents`;
- crea bookmarks/entries;
- usa `multiBuild()`.

Conceptualmente:

```python
from reportlab.platypus import TableOfContents
```

Y:

```python
doc.multiBuild(story)
```

Si se genera TOC, prueba que:
- los títulos aparezcan;
- los números de página sean correctos;
- los enlaces funcionen;
- el documento termine con el número correcto de páginas.

---

# 23. Bookmarks y enlaces

Para enlaces externos:

```python
canvas.linkURL(
    "https://example.com",
    rect=(x1, y1, x2, y2),
    relative=0,
)
```

Para enlaces internos/bookmarks, usa las APIs de Canvas/Platypus correspondientes y verifica el PDF final.

No generes URLs inválidas desde datos sin validación.

---

# 24. Metadatos PDF

Establece metadatos cuando sea útil:

```python
c.setTitle("Informe mensual")
c.setAuthor("Mi Empresa")
c.setSubject("Resumen financiero")
c.setKeywords("informe, finanzas, 2026")
```

Para documentos corporativos, evita información personal innecesaria en metadatos.

---

# 25. Gráficos

ReportLab Graphics permite crear dibujos vectoriales y gráficos.

Ejemplo:

```python
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.barcharts import VerticalBarChart

drawing = Drawing(400, 200)

chart = VerticalBarChart()
chart.x = 50
chart.y = 50
chart.height = 120
chart.width = 300
chart.data = [
    [10, 20, 30, 40],
]
chart.categoryAxis.categoryNames = [
    "Q1", "Q2", "Q3", "Q4"
]

drawing.add(chart)
```

Como `Drawing` puede actuar como flowable, puede incorporarse a una story.

Prefiere gráficos vectoriales cuando:
- el gráfico se genera desde datos;
- se necesita escalado;
- la impresión es importante.

---

# 26. Flowables personalizados

Cuando no exista un flowable adecuado, crea uno.

Patrón:

```python
from reportlab.platypus import Flowable

class Rule(Flowable):
    def __init__(self, width, thickness=1):
        super().__init__()
        self.width = width
        self.thickness = thickness
        self.height = thickness

    def wrap(self, availWidth, availHeight):
        return min(self.width, availWidth), self.height

    def draw(self):
        self.canv.setLineWidth(self.thickness)
        self.canv.line(0, 0, self.width, 0)
```

Regla importante:
- `wrap()` debe devolver dimensiones coherentes;
- `draw()` debe dibujar dentro del espacio calculado;
- si el flowable puede dividirse, implementa `split()` cuando sea necesario;
- no dependas de coordenadas globales dentro de un flowable.

---

# 27. Debug de layout

Cuando un PDF sale "mal":
1. reduce el problema a un ejemplo mínimo;
2. muestra bordes de frames;
3. revisa márgenes;
4. revisa `leading`;
5. revisa anchos de tabla;
6. revisa imágenes;
7. busca flowables que no puedan dividirse;
8. prueba con texto corto y largo.

Para frames:

```python
Frame(
    ...,
    showBoundary=1,
)
```

Para tablas, agrega temporalmente:
- `GRID`;
- backgrounds;
- paddings visibles.

Después elimina el debugging.

---

# 28. Problemas frecuentes y diagnóstico

## "El texto se sale"

Probables causas:
- `drawString` usado para texto largo;
- fuente demasiado grande;
- ancho insuficiente;
- falta de wrapping;
- tabla sin `Paragraph`.

Solución:
- usar `Paragraph`;
- ajustar estilo;
- definir `colWidths`;
- revisar el contenido real.

## "La tabla se corta"

Revisar:
- si puede dividirse;
- `repeatRows`;
- anchos;
- flowables dentro de celdas;
- filas extremadamente altas.

## "El título queda separado del contenido"

Usar:

```python
keepWithNext=True
```

o:

```python
KeepTogether([...])
```

## "El PDF solo funciona en mi máquina"

Revisar:
- fuentes;
- rutas;
- imágenes;
- dependencias;
- versión de ReportLab;
- directorio de trabajo actual.

## "Los acentos salen mal"

Revisar:
- fuente;
- encoding;
- registro de TTF;
- fuente realmente utilizada por el `ParagraphStyle`.

## "La imagen tiene proporciones incorrectas"

Calcular dimensiones conservando relación de aspecto.

## "La página queda con demasiado espacio"

Revisar:
- márgenes;
- paddings;
- `Spacer`;
- `leading`;
- alturas fijas;
- frames.

---

# 29. Arquitectura recomendada para proyectos reales

No pongas todo en `main.py`.

Preferir:

```text
project/
├── app/
│   ├── pdf/
│   │   ├── __init__.py
│   │   ├── document.py
│   │   ├── styles.py
│   │   ├── tables.py
│   │   ├── headers.py
│   │   ├── fonts.py
│   │   ├── images.py
│   │   └── components.py
│   ├── models/
│   └── services/
├── fonts/
├── assets/
├── tests/
├── requirements.txt
└── pyproject.toml
```

Separación:
- `models`: datos;
- `styles`: tipografía y colores;
- `components`: bloques reutilizables;
- `tables`: tablas;
- `headers`: encabezados/pies;
- `document`: composición final.

---

# 30. Patrón de documento reutilizable

```python
class ReportBuilder:
    def __init__(self, output_path):
        self.output_path = output_path

    def build(self, data):
        doc = self._create_document()
        story = self._build_story(data)
        doc.build(
            story,
            onFirstPage=self._draw_first_page,
            onLaterPages=self._draw_later_pages,
        )

    def _create_document(self):
        ...

    def _build_story(self, data):
        ...

    def _draw_first_page(self, canvas, doc):
        ...

    def _draw_later_pages(self, canvas, doc):
        ...
```

La API pública debe ser pequeña y clara.

---

# 31. Separar datos de presentación

Mala práctica:

```python
for row in rows:
    story.append(
        Paragraph(
            f"<b>{row['name']}</b> ...",
            ParagraphStyle(...),
        )
    )
```

Mejor:
- preparar datos;
- tener estilos centralizados;
- usar funciones/componentes para convertir datos a flowables.

Ejemplo:

```python
def build_customer_header(customer, styles):
    return [
        Paragraph(escape(customer.name), styles["customer_name"]),
        Paragraph(escape(customer.email), styles["small"]),
    ]
```

---

# 32. Validación y pruebas

Un PDF válido no implica un PDF correcto visualmente.

Pruebas mínimas:
- archivo creado;
- tamaño > 0;
- número esperado de páginas;
- texto esencial presente;
- tablas presentes;
- imágenes cargadas;
- fuentes disponibles;
- enlaces esperados;
- documento abre correctamente.

Cuando sea posible, usa una librería externa de lectura de PDF para pruebas estructurales.

Ejemplo conceptual:

```python
from pathlib import Path

output = Path("salida.pdf")
assert output.exists()
assert output.stat().st_size > 0
```

Para pruebas de regresión visual:
- generar PDF;
- rasterizar páginas;
- comparar imágenes;
- usar tolerancia para diferencias inevitables.

No dependas únicamente de comparación byte-a-byte: muchos PDFs válidos pueden diferir en bytes aunque visualmente sean equivalentes.

---

# 33. Casos de prueba obligatorios para documentos dinámicos

Si el contenido viene de datos externos, prueba:
1. datos vacíos;
2. una fila;
3. muchas filas;
4. texto largo;
5. texto con caracteres Unicode;
6. números grandes;
7. fechas;
8. imágenes ausentes;
9. imagen muy grande;
10. página con poco espacio restante;
11. tabla que cruza páginas;
12. documento de muchas páginas.

---

# 34. Rendimiento

Para generación masiva:
- evita cargar repetidamente la misma fuente;
- evita decodificar la misma imagen cientos de veces;
- reutiliza estilos;
- minimiza trabajo dentro de `onPage`;
- no construyas objetos enormes innecesariamente;
- considera procesamiento por lotes;
- mide antes de optimizar.

Si se generan miles de PDFs:
- separa datos, assets y renderizado;
- usa workers si el entorno lo permite;
- controla memoria;
- asegúrate de cerrar/liberar recursos.

No sacrifiques legibilidad del código por microoptimizaciones no medidas.

---

# 35. Seguridad

Si el contenido viene del usuario:
- escapa markup de `Paragraph`;
- valida rutas de archivos;
- no permitas que una ruta externa arbitraria acceda al sistema;
- valida URLs si se generan enlaces;
- no descargues recursos remotos sin una política clara;
- no ejecutes contenido proveniente del PDF o de datos como código;
- evita incluir secretos en metadatos.

Nunca interpolar sin escape:

```python
Paragraph(user_text, style)
```

cuando `user_text` puede contener `<`, `>` o markup no deseado.

Preferir:

```python
Paragraph(escape(user_text), style)
```

---

# 36. Diseño visual

Un PDF profesional normalmente necesita:
- jerarquía tipográfica clara;
- márgenes consistentes;
- espacios consistentes;
- paleta pequeña;
- tablas legibles;
- alineación;
- suficiente contraste;
- números alineados de forma coherente;
- encabezados repetidos;
- páginas numeradas.

No sobrecargues el documento con:
- demasiados colores;
- demasiadas fuentes;
- bordes en todas partes;
- sombras innecesarias;
- tamaños arbitrarios.

---

# 37. Accesibilidad y calidad documental

Cuando el caso lo requiera, considera:
- contraste;
- tamaño legible;
- estructura semántica razonable;
- texto real en vez de imágenes de texto;
- orden de lectura;
- etiquetas/estructura de accesibilidad si la versión y el flujo de trabajo lo soportan.

No afirmes que un PDF es "accesible" solo porque contiene texto seleccionable. La accesibilidad PDF es un problema más amplio.

Si el usuario solicita PDF/UA, WCAG o accesibilidad formal, identifica explícitamente las limitaciones de ReportLab y valida con herramientas específicas.

---

# 38. Formularios PDF

Si el usuario pide formularios:
- evalúa `AcroForm` de Canvas;
- define campos con nombres únicos;
- configura valores y apariencias;
- prueba en diferentes lectores PDF.

No confundas:
- formulario interactivo PDF;
- PDF estático con espacios para escribir;
- HTML imprimible.

Pregunta o infiere correctamente cuál necesita.

---

# 39. Facturas

Para facturas:
- datos del emisor;
- cliente;
- número;
- fecha;
- moneda;
- líneas;
- subtotal;
- impuestos;
- descuentos;
- total;
- condiciones;
- método de pago.

Usa tablas para líneas y `Paragraph` para descripciones.

Los importes deben estar alineados y calculados fuera de la capa de presentación.

Nunca dependas de texto renderizado para realizar cálculos monetarios.

---

# 40. Documentos legales

Para contratos:
- usa estilos de párrafo consistentes;
- numeración estable;
- encabezados;
- páginas;
- control de saltos;
- fechas y nombres escapados;
- evita truncar texto.

Si hay requisitos jurídicos específicos, no inventes garantías sobre validez legal.

---

# 41. Catálogos

Para catálogos:
- usa grids o tablas;
- normaliza tamaños de imagen;
- reutiliza estilos;
- considera `KeepTogether` para tarjeta + título + precio;
- prueba productos con nombres muy largos.

---

# 42. Recibos y tickets

Para tickets pequeños:
- Canvas suele ser más directo;
- usa el tamaño de papel real;
- evita márgenes innecesarios;
- controla fuentes;
- mide el ancho del texto.

Si el ancho es fijo:

```python
from reportlab.pdfbase.pdfmetrics import stringWidth

width = stringWidth("Texto", "Helvetica", 10)
```

Esto permite calcular alineación.

---

# 43. Exportación desde datos JSON/CSV

Patrón:

```python
def render_report(records, output_path):
    story = []

    for record in records:
        story.extend(build_record(record))

    doc.build(story)
```

No mezcles:
- lectura de CSV;
- reglas de negocio;
- generación de PDF;
- escritura del archivo;

en una única función.

---

# 44. Fechas, números y moneda

Formatea los datos antes de construir flowables.

Ejemplo conceptual:

```python
def format_currency(value):
    return f"${value:,.2f}"
```

Para producción internacional:
- considera locale;
- moneda;
- separador decimal;
- zona horaria;
- formato de fecha.

No asumas que `$` significa USD si el proyecto usa otra moneda.

---

# 45. Rutas y assets

Usa `pathlib`:

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parent
logo = ROOT / "assets" / "logo.png"
```

No dependas de:

```python
"assets/logo.png"
```

si el script puede ejecutarse desde otro directorio.

---

# 46. Código que debes evitar

Evita:
- cientos de coordenadas mágicas;
- estilos repetidos;
- una función de 1000 líneas;
- texto largo con `drawString`;
- tablas con strings enormes sin wrapping;
- rutas relativas frágiles;
- fuentes registradas repetidamente;
- lógica de negocio dentro de `onPage`;
- `PageBreak` como solución universal;
- `KeepTogether` para envolver documentos gigantes;
- imágenes sin control de tamaño;
- asumir que todo PDF generado es visualmente correcto.

---

# 47. Estrategia de implementación cuando el usuario pide "hazme un PDF"

Antes de escribir código:

1. Identifica:
   - tipo de documento;
   - tamaño de página;
   - orientación;
   - número aproximado de páginas;
   - contenido dinámico;
   - tablas;
   - imágenes;
   - fuentes;
   - encabezados/pies;
   - branding.

2. Decide:
   - Canvas;
   - Platypus;
   - híbrido.

3. Define:
   - estilos;
   - márgenes;
   - componentes;
   - estructura de datos.

4. Implementa una primera versión funcional.

5. Añade:
   - wrapping;
   - paginación;
   - tablas;
   - encabezados/pies;
   - assets.

6. Prueba con casos extremos.

7. Revisa visualmente.

8. Refactoriza.

---

# 48. Checklist de revisión de código ReportLab

Antes de entregar:

- [ ] ¿Se usa Canvas o Platypus de forma apropiada?
- [ ] ¿Los tamaños de página usan constantes de ReportLab?
- [ ] ¿Las unidades usan `mm`, `cm` o `inch` cuando corresponde?
- [ ] ¿Los estilos están centralizados?
- [ ] ¿El texto largo usa `Paragraph`?
- [ ] ¿Las tablas tienen anchos razonables?
- [ ] ¿Las tablas usan `repeatRows` cuando cruzan páginas?
- [ ] ¿Las imágenes mantienen proporción?
- [ ] ¿Las fuentes soportan los caracteres necesarios?
- [ ] ¿Las rutas de assets son robustas?
- [ ] ¿Se escapa contenido dinámico?
- [ ] ¿Se usa `saveState`/`restoreState` en helpers de Canvas?
- [ ] ¿Los encabezados/pies se dibujan en el lugar correcto?
- [ ] ¿Los títulos evitan quedar huérfanos?
- [ ] ¿Se probaron varias páginas?
- [ ] ¿Se probaron textos largos?
- [ ] ¿Se probaron caracteres Unicode?
- [ ] ¿Se probó una tabla grande?
- [ ] ¿Se abrió y verificó el PDF generado?
- [ ] ¿Se evitaron dependencias innecesarias?
- [ ] ¿La API pública del generador es sencilla?

---

# 49. Patrón recomendado de solución completa

Cuando el usuario pida un reporte, intenta llegar a una estructura de este estilo:

```python
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


class ReportPDF:
    def __init__(self, output_path: str):
        self.output_path = Path(output_path)
        self.styles = self._build_styles()

    def _build_styles(self):
        return {
            "title": ParagraphStyle(
                "Title",
                fontName="Helvetica-Bold",
                fontSize=20,
                leading=24,
                textColor=colors.HexColor("#111827"),
                spaceAfter=8 * mm,
            ),
            "body": ParagraphStyle(
                "Body",
                fontName="Helvetica",
                fontSize=9.5,
                leading=13,
                textColor=colors.HexColor("#374151"),
                spaceAfter=4 * mm,
            ),
            "table": ParagraphStyle(
                "Table",
                fontName="Helvetica",
                fontSize=8,
                leading=10,
            ),
        }

    def build(self, data):
        doc = SimpleDocTemplate(
            str(self.output_path),
            pagesize=A4,
            leftMargin=18 * mm,
            rightMargin=18 * mm,
            topMargin=22 * mm,
            bottomMargin=18 * mm,
        )

        story = []
        story.extend(self._build_content(data))

        doc.build(
            story,
            onFirstPage=self._draw_page,
            onLaterPages=self._draw_page,
        )

    def _build_content(self, data):
        story = [
            Paragraph(
                escape(data["title"]),
                self.styles["title"],
            )
        ]

        # Construir aquí componentes del documento.

        return story

    def _draw_page(self, canvas, doc):
        canvas.saveState()
        width, _ = A4

        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#6B7280"))
        canvas.drawRightString(
            width - 18 * mm,
            10 * mm,
            f"Página {doc.page}",
        )

        canvas.restoreState()
```

Este patrón no es obligatorio. Adáptalo al caso real.

---

# 50. Cómo responder ante errores de ReportLab

Cuando el usuario pegue un traceback:

1. identifica la excepción exacta;
2. identifica el flowable implicado;
3. determina si es un problema de:
   - dimensiones;
   - splitting;
   - fuente;
   - markup;
   - tabla;
   - ruta;
   - imagen;
   - versión;
4. explica la causa;
5. ofrece el cambio mínimo correcto;
6. si hace falta, proporciona una versión refactorizada.

No "soluciones" un error eliminando funcionalidad sin explicar el impacto.

---

# 51. Regla para APIs desconocidas

Si no conoces con certeza una API concreta de la versión instalada:
- no inventes nombres de métodos;
- consulta la documentación o el código instalado si está disponible;
- comprueba la versión;
- usa APIs estables y documentadas.

ReportLab tiene muchas áreas avanzadas. Es preferible una solución conservadora y verificable que una API inventada.

---

# 52. Fuentes oficiales de referencia

Usa como referencia principal la documentación oficial de ReportLab:
- User Guide;
- documentación de Platypus;
- capítulos de Paragraphs y Tables;
- documentación de fonts;
- documentación de graphics;
- documentación de instalación.

Para GitHub Copilot, recuerda que esta skill es un conjunto de instrucciones para el agente, no un paquete Python.

---

# 53. Regla final de calidad

Cada vez que generes código ReportLab, intenta que cumpla esta secuencia:

```text
Datos
  ↓
Normalización / validación
  ↓
Estilos
  ↓
Componentes / Flowables
  ↓
Documento / Templates
  ↓
Renderizado PDF
  ↓
Validación
  ↓
Revisión visual
```

Si el usuario solo necesita un ejemplo pequeño, no sobrearquitectures.

Si el usuario necesita una aplicación real, aplica la arquitectura completa.

Si el usuario pide "hazlo bonito", mejora primero:
1. jerarquía;
2. espaciado;
3. tipografía;
4. alineación;
5. tablas;
6. consistencia;
y después añade decoración.

Si el usuario pide un PDF exacto respecto a una imagen o diseño existente, prioriza medición, coordenadas, tamaños, fuentes y pruebas visuales sobre abstracciones innecesarias.
