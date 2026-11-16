# NovaRetail Financial GenAI

Sistema académico reproducible para generar, exportar, validar y visualizar datos financieros y operativos completamente sintéticos de una empresa ficticia de comercio electrónico.

## Estado del proyecto

- **Versión:** 0.2.0
- **Estado:** Funcional, probado, depurado y publicado
- **Responsable:** ELVER ALIRIO ALVAREZ RAMIREZ
- **Uso:** Exclusivamente académico
- **Empresa simulada:** NovaRetail Colombia S.A.S.
- **Periodo:** Enero de 2023 a diciembre de 2025
- **Moneda:** Pesos colombianos
- **Pruebas verificadas:** 380 aprobadas
- **Advertencias controladas:** 1
- **Aplicación pública:** https://novaretail-financial-genai.streamlit.app
- **Release:** https://github.com/ElverAAlvarez32/novaretail-financial-genai/releases/tag/v0.2.0

## Advertencia sobre los datos

Todos los productos, clientes, pedidos, devoluciones, campañas, presupuestos, estados financieros y resultados son sintéticos.

NovaRetail Colombia S.A.S. es una empresa ficticia. Ningún registro corresponde a una persona u organización real.

Los resultados no deben utilizarse para decisiones empresariales, financieras, crediticias, contables, laborales o de inversión.

## Contexto académico

El proyecto se desarrolló para el caso práctico de la asignatura **Aplicaciones de Negocio y Gestión de Riesgos**.

La versión actual integra:

- Generación reproducible de datos sintéticos.
- Estados financieros mensuales.
- Presupuesto y ejecución.
- Datos operativos de comercio electrónico.
- Exportación profesional a Excel.
- Validación estructural.
- Validación de calidad.
- Validación contable.
- Validación relacional.
- Pruebas automatizadas.
- Tablero ejecutivo con Streamlit y Plotly.
- Despliegue público mediante Streamlit Community Cloud.
- Control de versiones y lanzamientos en GitHub.

## Alcance funcional implementado

### Generación de datos

El sistema genera:

- 120 productos.
- 4.000 clientes.
- 18.072 pedidos.
- 23.706 líneas de pedido.
- 3.712 registros de inventario.
- 1.511 devoluciones.
- 216 registros de marketing.
- 36 estados de resultados.
- 36 balances generales.
- 36 flujos de efectivo.
- 288 registros presupuestales.

La generación utiliza una semilla configurada para mantener la reproducibilidad bajo las mismas versiones, parámetros y dependencias.

### Estados financieros

El proyecto construye:

- Estado de resultados.
- Balance general.
- Flujo de efectivo por método indirecto.
- Presupuesto frente a ejecución.

Las principales conciliaciones son:

```text
Ingresos netos =
Ingresos brutos
- Descuentos
- Devoluciones
```

```text
Utilidad bruta =
Ingresos netos
- Costo de mercancía vendida
```

```text
Activo total =
Pasivo total
+ Patrimonio
```

```text
Efectivo final =
Efectivo inicial
+ Variación neta del efectivo
```

```text
Inventario final =
Inventario inicial
+ Compras
+ Devoluciones
+ Ajustes
- Ventas
```

### Libro Excel

El resultado principal es:

```text
data/raw/NovaRetail_Datos_RAW_v01.xlsx
```

El libro contiene 12 hojas:

1. `00_Control`
2. `01_Parametros`
3. `02_Productos`
4. `03_Clientes`
5. `04_Pedidos`
6. `05_Inventario`
7. `06_Devoluciones`
8. `07_Marketing`
9. `08_Estado_Resultados`
10. `09_Balance_General`
11. `10_Flujo_Efectivo`
12. `11_Presupuesto`

El archivo incorpora:

- Tablas estructuradas de Excel.
- Encabezados formateados.
- Filtros.
- Paneles inmovilizados.
- Cuadrículas ocultas.
- Formatos monetarios y porcentuales.
- Metadatos documentales.
- Advertencias sobre el carácter sintético de los datos.

## Validaciones

El libro se revisa mediante cuatro capas.

### Validación estructural

Comprueba hojas, columnas, claves primarias, valores obligatorios, periodos financieros e indicadores de datos sintéticos.

### Validación de calidad

Comprueba valores nulos, duplicados, fechas, tipos, rangos permitidos y valores atípicos mediante IQR. Los valores atípicos son alertas de revisión y no errores automáticos.

### Validación contable

Comprueba 15 reglas, incluyendo ingresos netos, utilidades, ecuación del balance, efectivo e inventario. La diferencia máxima verificada es cero.

### Validación relacional

Comprueba nueve relaciones entre pedidos, productos, clientes, devoluciones e inventario. El resultado verificado es cero registros huérfanos y cero registros afectados.

## Tablero ejecutivo

La aplicación pública está disponible en:

https://novaretail-financial-genai.streamlit.app

El tablero incluye:

- Resumen ejecutivo.
- Estado de resultados.
- Inventario de datos.
- Filtros por periodo.
- Tarjetas KPI.
- Gráficos de área, líneas, barras y dona.
- Información emergente y tablas desplazables.

## Indicadores verificados del tablero

Para enero de 2023 a diciembre de 2025:

- Productos: 120.
- Clientes: 4.000.
- Pedidos: 18.072.
- Líneas de pedido: 23.706.
- Devoluciones: 1.511.
- Ingresos netos: 76.959.255.100 pesos.
- Utilidad neta: 3.425.293.548 pesos.
- Margen neto promedio aproximado: 4,42 %.
- Hojas del libro: 12.
- Registros totales: 33.740.

## Arquitectura del proyecto

```text
novaretail_financial_genai/
├── .streamlit/
│   └── config.toml
├── config/
├── data/
│   └── raw/
│       └── NovaRetail_Datos_RAW_v01.xlsx
├── docs/
├── prompts/
├── scripts/
│   ├── generate_data.py
│   └── validate_data.py
├── src/
│   └── novaretail/
│       ├── app/
│       ├── generation/
│       ├── reporting/
│       └── validation/
├── tests/
├── pyproject.toml
├── requirements.txt
└── streamlit_app.py
```

## Tecnologías utilizadas

- Python 3.11 para desarrollo local.
- pandas.
- NumPy.
- openpyxl.
- PyYAML.
- Pydantic.
- python-dotenv.
- Streamlit.
- Plotly.
- pytest.
- Git y GitHub.
- GitHub CLI.
- Streamlit Community Cloud.
- Visual Studio Code.
- PowerShell.

## Instalación local

### Crear y activar el entorno virtual

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Instalar dependencias

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

## Ejecución

### Generar el libro Excel

```powershell
python scripts\generate_data.py
```

### Validar el libro

```powershell
python scripts\validate_data.py
```

### Ejecutar el tablero localmente

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

## Pruebas

Resultado verificado del tablero:

```text
23 passed in 13.19s
```

Resultado verificado de la suite completa:

```text
380 passed, 1 warning
```

La advertencia corresponde a una prueba que introduce deliberadamente una fecha inválida para comprobar su detección. No representa una falla funcional.

## Calidad y reproducibilidad

El proyecto utiliza la semilla:

```text
20261104
```

La reproducibilidad requiere la misma versión del código, parámetros YAML, semilla y dependencias compatibles.

## Seguridad y privacidad

- No se utilizan datos personales reales.
- No se utiliza información empresarial confidencial.
- No se almacenan credenciales en el código.
- `.env` está excluido de Git.
- El libro contiene únicamente información sintética.
- La aplicación pública no solicita datos al usuario.
- No se envían datos sensibles a modelos externos.
- La aplicación no incluye autenticación individual.

## Control de versiones

Repositorio:

https://github.com/ElverAAlvarez32/novaretail-financial-genai

Versiones publicadas:

- `v0.1.0`: generación, Excel y validaciones.
- `v0.2.0`: tablero interactivo, despliegue público y 380 pruebas.

Release actual:

https://github.com/ElverAAlvarez32/novaretail-financial-genai/releases/tag/v0.2.0

## Capacidades no implementadas

Las siguientes capacidades no forman parte de `v0.2.0`:

- Integración con un modelo LLM.
- Interpretación automática mediante IA generativa.
- Auditoría o validación de respuestas generativas.
- Simulación independiente de escenarios financieros.
- Proceso CLEAN separado.
- Módulo EDA independiente.
- Cálculo especializado de ROA, ROE, liquidez y endeudamiento.
- Informe académico generado automáticamente.
- Autenticación y autorización de usuarios.

Estas capacidades podrán añadirse posteriormente mediante requisitos, arquitectura, código y pruebas específicos. No se conservan módulos vacíos para representar funcionalidades inexistentes.

## Limitaciones

- Es un caso académico, no una empresa real.
- El tablero depende del libro Excel incluido en el repositorio.
- El despliegue público permite acceso sin credenciales.
- Los valores atípicos requieren interpretación humana.
- Las cifras no deben utilizarse para decisiones reales.
- No se ha integrado un proveedor de IA generativa.
- No existen métricas reales de ahorro o impacto empresarial.

## Estado final de v0.2.0

| Componente | Estado |
|---|---|
| Configuración YAML | Implementada |
| Generación sintética | Aprobada |
| Libro Excel | Generado |
| Validación estructural | Aprobada |
| Validación de calidad | Aprobada |
| Validación contable | Aprobada |
| Validación relacional | Aprobada |
| Tablero Streamlit | Implementado |
| Despliegue público | Activo |
| Pruebas automáticas | 380 aprobadas |
| Integración con LLM | No implementada |
| Escenarios independientes | No implementados |
| Proceso CLEAN independiente | No implementado |

## Conclusión

NovaRetail Financial GenAI `v0.2.0` ofrece un flujo reproducible para generar, exportar, validar, probar y visualizar datos financieros y operativos sintéticos.

El núcleo funcional está probado y publicado. Las capacidades no implementadas se declaran expresamente para evitar atribuir al proyecto funciones que todavía no existen.
