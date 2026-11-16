## NovaRetail Financial GenAI v0.2.0

Segunda versión funcional del proyecto académico NovaRetail Financial GenAI.

Esta versión incorpora un tablero ejecutivo interactivo, su despliegue público mediante Streamlit Community Cloud y pruebas automatizadas para la nueva capa de visualización.

## Novedades principales

### Tablero ejecutivo interactivo

- Aplicación web desarrollada con Streamlit.
- Tema visual oscuro y componentes personalizados.
- Navegación lateral entre las diferentes secciones.
- Filtros globales por periodo.
- Tarjetas visuales de indicadores financieros y operativos.
- Gráficos interactivos desarrollados con Plotly.
- Diseño adaptable para consulta en diferentes tamaños de pantalla.

### Resumen ejecutivo

El tablero presenta:

- Ingresos netos acumulados.
- Utilidad neta acumulada.
- Margen neto promedio.
- Pedidos únicos.
- Líneas de pedido procesadas.
- Productos disponibles.
- Clientes sintéticos.
- Devoluciones registradas.
- Tasa de devolución.
- Evolución mensual de ingresos y utilidades.
- Ventas netas por categoría.
- Participación de ventas por canal.

### Estado de resultados

La aplicación permite consultar:

- Ingresos netos.
- Utilidad bruta.
- Utilidad operacional.
- Utilidad neta.
- Margen bruto.
- Margen operacional.
- Margen neto.
- Evolución mensual de resultados.
- Evolución mensual de márgenes.
- Detalle financiero por periodo.

### Inventario de datos

Se agregó una vista técnica con:

- Cantidad de hojas del libro.
- Número total de registros.
- Volumen aproximado de celdas.
- Registros por hoja.
- Tabla detallada de filas, columnas y celdas.

## Interactividad

La aplicación incorpora:

- Filtros de periodo inicial y final.
- Información emergente en gráficos.
- Gráficos de área, barras, dona y líneas.
- Tablas desplazables.
- Navegación lateral.
- Actualización de indicadores según el periodo seleccionado.

## Compatibilidad de datos

Se incluyeron normalizaciones internas para respetar la estructura real del libro sin modificar el archivo Excel:

- `periodo_devolucion` se utiliza internamente como `periodo` para filtrar las devoluciones.
- La visualización comercial utiliza la columna real `canal` de la hoja `04_Pedidos`.
- El archivo `NovaRetail_Datos_RAW_v01.xlsx` permanece como fuente del tablero.
- Todos los datos continúan siendo completamente sintéticos.

## Despliegue público

La aplicación fue desplegada correctamente en Streamlit Community Cloud.

### Enlace público

https://novaretail-financial-genai.streamlit.app

### Configuración del despliegue

- Repositorio: `ElverAAlvarez32/novaretail-financial-genai`
- Rama: `main`
- Aplicación principal: `src/novaretail/app/streamlit_app.py`
- Ejecución en modo `headless`
- Datos sintéticos incluidos para permitir el funcionamiento remoto
- Importación del paquete corregida para el entorno de Streamlit Community Cloud

## Calidad y pruebas

Se agregaron 23 pruebas automatizadas para el tablero.

Las pruebas verifican:

- Existencia y ubicación del libro principal.
- Carga de las 12 hojas.
- Rechazo de archivos inexistentes.
- Normalización de `periodo_devolucion`.
- Ordenamiento de periodos.
- Inclusión de los límites en los filtros.
- Cobertura de los 36 periodos financieros.
- Formato de números enteros.
- Formato de porcentajes.
- Formato monetario abreviado.
- Construcción del gráfico financiero.
- Construcción del gráfico de márgenes.
- Agrupación de ventas por categoría.
- Uso de la columna real `canal`.
- Volúmenes conocidos del conjunto de datos.
- Totales financieros publicados en el tablero.

### Resultado verificado del tablero

```text
23 passed in 13.19s
```

### Resultado verificado de la suite completa

```text
380 passed, 1 warning in 2369.11s
```

La única advertencia corresponde a una prueba que introduce deliberadamente una fecha inválida para comprobar que el validador detecte valores no interpretables. No representa una falla funcional.

## Indicadores verificados

El tablero presenta, para el periodo completo de enero de 2023 a diciembre de 2025:

- 120 productos.
- 4.000 clientes.
- 18.072 pedidos.
- 23.706 líneas de pedido.
- 1.511 devoluciones.
- 12 hojas de datos.
- 33.740 registros totales.
- 76.959.255.100 pesos de ingresos netos acumulados.
- 3.425.293.548 pesos de utilidad neta acumulada.
- Margen neto promedio aproximado de 4,42 %.

## Componentes incorporados

### Configuración visual

```text
.streamlit/config.toml
```

### Tema y componentes del tablero

```text
src/novaretail/app/dashboard_theme.py
```

### Aplicación principal

```text
src/novaretail/app/streamlit_app.py
```

### Punto de entrada para despliegue

```text
streamlit_app.py
```

### Pruebas automatizadas

```text
tests/test_streamlit_app.py
```

### Fuente de datos sintéticos

```text
data/raw/NovaRetail_Datos_RAW_v01.xlsx
```

## Comandos principales

### Generar los datos

```powershell
python scripts\generate_data.py
```

### Validar el libro

```powershell
python scripts\validate_data.py
```

### Abrir el tablero localmente

```powershell
python -m streamlit run "src\novaretail\app\streamlit_app.py" --server.port 8501
```

### Ejecutar las pruebas del tablero

```powershell
python -m pytest tests/test_streamlit_app.py -v
```

### Ejecutar la suite completa

```powershell
python -m pytest tests -q
```

## Cambios técnicos relevantes

- Se habilitó el modo `headless` para el despliegue remoto.
- Se agregó la carpeta `src` al entorno de importación de Python en Streamlit Community Cloud.
- Se creó un punto de entrada en la raíz del repositorio.
- Se agregó un tema visual centralizado.
- Se corrigieron las importaciones del paquete `novaretail`.
- Se incorporó el archivo Excel sintético necesario para el despliegue.
- Se mantuvo la ejecución local compatible con Windows y PowerShell.
- Se eliminó el aviso visual redundante solicitado durante la revisión del tablero.

## Diferencias respecto a v0.1.0

La versión `v0.1.0` consolidó:

- Generación de datos sintéticos.
- Exportación a Excel.
- Validación estructural.
- Validación de calidad.
- Validación contable.
- Validación relacional.
- Suite original de 357 pruebas.

La versión `v0.2.0` agrega:

- Tablero ejecutivo interactivo.
- Visualizaciones financieras y operativas.
- Filtros globales.
- Publicación mediante enlace web.
- Compatibilidad con Streamlit Community Cloud.
- 23 pruebas específicas del tablero.
- Suite ampliada a 380 pruebas aprobadas.

## Limitaciones

- Los datos no representan una empresa real.
- El tablero no debe utilizarse para tomar decisiones empresariales.
- La aplicación publicada depende del archivo Excel sintético incluido en el repositorio.
- Las observaciones atípicas detectadas mediante IQR son alertas de revisión y no errores confirmados.
- La aplicación no incluye autenticación individual de usuarios.
- El enlace público permite consultar el tablero sin credenciales.

## Advertencia académica

Todos los productos, clientes, pedidos, devoluciones, campañas, estados financieros, presupuestos y resultados son completamente sintéticos.

NovaRetail Colombia S.A.S. es una empresa ficticia creada exclusivamente para fines académicos.

El proyecto no debe emplearse para decisiones comerciales, financieras, contables, crediticias, laborales o de inversión sobre personas u organizaciones reales.