# NovaRetail Financial GenAI

Prototipo académico de análisis financiero y operativo con inteligencia artificial generativa para una empresa ficticia de comercio electrónico.

## Estado del proyecto

**Versión:** 0.1.0  
**Fase actual:** Configuración inicial  
**Estado:** En desarrollo  
**Responsable:** ELVER ALIRIO ALVAREZ RAMIREZ  
**Uso:** Exclusivamente académico  

## Advertencia sobre los datos

Todos los datos que se utilizarán en este proyecto serán sintéticos.

La empresa NovaRetail Colombia S.A.S., sus clientes, productos, proveedores, transacciones, estados financieros, presupuestos, campañas y resultados son completamente ficticios.

Ningún dato corresponde a una empresa o persona real.

Los resultados obtenidos no deben presentarse como hechos financieros observados ni utilizarse para tomar decisiones reales.

## Contexto académico

El proyecto se desarrolla para el caso práctico de la asignatura:

**Aplicaciones de Negocio y Gestión de Riesgos**

El prototipo busca integrar:

- Análisis exploratorio de datos, EDA.
- Análisis financiero.
- Indicadores de comercio electrónico.
- Inteligencia artificial generativa.
- Prompt Engineering.
- Simulación de escenarios.
- Validación de resultados.
- Gestión de riesgos.
- Trazabilidad.
- Supervisión humana.

## Problema preliminar

El análisis financiero requiere reunir información de diferentes fuentes, validar su consistencia, calcular indicadores, comparar periodos y explicar los hallazgos a diferentes audiencias.

Cuando estas actividades se realizan de manera manual pueden presentarse:

- Errores en fórmulas.
- Comparaciones entre periodos incompatibles.
- Confusión entre monedas o unidades.
- Omisión de datos relevantes.
- Interpretaciones sin evidencia suficiente.
- Retrasos en la preparación de informes.
- Dificultad para convertir cifras en explicaciones claras.

La formulación definitiva del problema será aprobada después de generar y analizar el conjunto de datos sintético.

## Solución preliminar

El proyecto propone construir un asistente que permita:

1. Cargar datos financieros y operativos.
2. Validar estructura, tipos y relaciones.
3. Detectar problemas de calidad.
4. Limpiar los datos mediante reglas documentadas.
5. Calcular indicadores financieros.
6. Calcular indicadores de comercio electrónico.
7. Ejecutar análisis horizontal y vertical.
8. Crear visualizaciones.
9. Simular escenarios financieros.
10. Generar interpretaciones mediante IA generativa.
11. Verificar las respuestas generadas.
12. Solicitar revisión humana.
13. Exportar informes y evidencias.

## Principio de funcionamiento

Los cálculos financieros se realizarán mediante código reproducible.

La inteligencia artificial generativa se utilizará para:

- Explicar resultados.
- Resumir hallazgos.
- Comparar periodos.
- Formular preguntas de revisión.
- Generar recomendaciones condicionadas.
- Adaptar el lenguaje a una audiencia técnica o ejecutiva.

La inteligencia artificial generativa no será la fuente principal de los cálculos.

## Flujo previsto

```text
Parámetros documentados
        ↓
Generación de datos sintéticos
        ↓
Archivo RAW
        ↓
Validación de calidad
        ↓
Limpieza documentada
        ↓
Archivo CLEAN
        ↓
EDA y cálculos financieros
        ↓
Visualizaciones y escenarios
        ↓
Interpretación con IA generativa
        ↓
Verificación de la respuesta
        ↓
Revisión humana
        ↓
Informe final
```

## Periodo de análisis

El conjunto de datos cubrirá:

- **Fecha inicial:** enero de 2023.
- **Fecha final:** diciembre de 2025.
- **Frecuencia financiera:** mensual.
- **Número de periodos:** 36.
- **Moneda:** pesos colombianos, COP.
- **Unidad financiera:** miles de pesos colombianos.

## Volumen previsto

Los siguientes valores corresponden al diseño del conjunto de datos y podrán ajustarse antes de ejecutar el generador:

| Componente | Volumen previsto |
|---|---:|
| Productos ficticios | 120 |
| Clientes ficticios | 4.000 |
| Líneas de pedido | Entre 20.000 y 25.000 |
| Periodos financieros | 36 |
| Canales de marketing | 6 |
| Registros mensuales de inventario | 4.320 |

## Indicadores financieros previstos

### Liquidez

- Razón corriente.
- Prueba ácida.
- Capital de trabajo.

### Endeudamiento

- Endeudamiento total.
- Deuda sobre patrimonio.
- Cobertura de intereses.

### Rentabilidad

- Margen bruto.
- Margen operacional.
- Margen neto.
- Rentabilidad sobre activos, ROA.
- Rentabilidad sobre patrimonio, ROE.

### Eficiencia

- Rotación de inventarios.
- Días de inventario.
- Rotación de cartera.
- Periodo promedio de cobro.
- Rotación de activos.

## Indicadores de comercio electrónico previstos

- Ventas netas.
- Número de pedidos.
- Unidades vendidas.
- Ticket promedio.
- Margen por pedido.
- Tasa de devolución.
- Tasa de cancelación.
- Tiempo promedio de entrega.
- Clientes recurrentes.
- Ventas por canal.
- Ventas por categoría.
- Tasa de conversión.
- Costo de adquisición.
- Retorno publicitario.
- Quiebres de inventario.

## Arquitectura del proyecto

```text
novaretail_financial_genai/
│
├── config/       Configuración y reglas externas
├── data/         Datos RAW, CLEAN, referencias y muestras
├── docs/         Documentación y trazabilidad
├── notebooks/    Análisis exploratorio inicial
├── outputs/      Gráficos, informes, logs y evidencias
├── prompts/      Biblioteca versionada de prompts
├── scripts/      Puntos de entrada para ejecutar procesos
├── src/          Código fuente modular
└── tests/        Pruebas automáticas
```

## Tecnologías previstas

- Python.
- Visual Studio Code.
- pandas.
- NumPy.
- openpyxl.
- PyYAML.
- Pydantic.
- python-dotenv.
- Streamlit.
- Plotly.
- Matplotlib.
- pytest.
- Git.

El proveedor y el modelo de IA generativa se definirán después de confirmar las herramientas autorizadas.

## Calidad y reproducibilidad

El proyecto utilizará una semilla fija:

```text
20261104
```

Esta semilla permitirá reproducir el mismo conjunto de datos bajo la misma versión del código, los mismos parámetros y las mismas dependencias.

Las validaciones incluirán:

- Unicidad de identificadores.
- Integridad entre tablas.
- Tipos de datos.
- Fechas válidas.
- Moneda y unidad.
- Valores faltantes.
- Registros duplicados.
- Valores extremos.
- Consistencia del inventario.
- Consistencia del flujo de efectivo.
- Igualdad contable.
- Manejo de divisiones por cero.

## Controles contables previstos

```text
Activo total = Pasivo total + Patrimonio
```

```text
Efectivo final =
Efectivo inicial + Variación neta del efectivo
```

```text
Inventario final =
Inventario inicial
+ Compras
+ Devoluciones
+ Ajustes
- Ventas
```

```text
Ingresos netos =
Ingresos brutos
- Descuentos
- Devoluciones
```

## Seguridad y privacidad

El proyecto aplicará estas reglas:

- No utilizar datos personales reales.
- No utilizar información empresarial confidencial.
- No guardar credenciales dentro del código.
- Utilizar variables de entorno cuando sea necesario.
- Excluir el archivo `.env` del control de versiones.
- No enviar información sensible a servicios no autorizados.
- Registrar las interacciones relevantes con IA.
- Mantener revisión humana sobre las salidas.
- Separar datos originales, datos procesados y resultados.

## Trazabilidad de IA

Cada interacción relevante deberá registrar:

- Fecha.
- Caso de prueba.
- Archivo de entrada.
- Herramienta y modelo.
- Versión del prompt.
- Contexto suministrado.
- Respuesta original.
- Evaluación.
- Corrección aplicada.
- Decisión humana.
- Versión final aprobada.

## Reglas de desarrollo

El código deberá aplicar:

- PEP 8.
- Type hints.
- Docstrings.
- Funciones pequeñas y reutilizables.
- Excepciones específicas.
- Logging.
- Configuración externa.
- Pruebas automáticas.
- Control de versiones.
- Separación entre generación, validación, limpieza, análisis, IA e interfaz.

## Instalación

La instalación todavía no ha sido ejecutada.

Los comandos definitivos se agregarán después de validar:

- Versión de Python.
- Sistema operativo.
- Intérprete seleccionado.
- Entorno virtual.
- Compatibilidad de dependencias.

## Ejecución

La ejecución todavía no está disponible.

Los puntos de entrada previstos son:

```text
scripts/generate_data.py
scripts/validate_data.py
scripts/clean_data.py
scripts/run_eda.py
scripts/run_app.py
```

## Pruebas

Las pruebas automáticas se implementarán progresivamente en la carpeta:

```text
tests/
```

No se afirma que el código funciona o que las pruebas fueron aprobadas hasta ejecutar y registrar las validaciones correspondientes.

## Estado por componentes

| Componente | Estado |
|---|---|
| Estructura de carpetas | Creada |
| Archivos base | Creados |
| README | En configuración |
| Entorno virtual | Pendiente |
| Dependencias | Pendientes |
| Configuración YAML | Pendiente |
| Generador de datos | Pendiente |
| Archivo RAW | Pendiente |
| Validación | Pendiente |
| Archivo CLEAN | Pendiente |
| EDA | Pendiente |
| Indicadores financieros | Pendientes |
| Escenarios | Pendientes |
| Prompts | Pendientes |
| Integración con IA | Pendiente |
| Interfaz Streamlit | Pendiente |
| Informe académico | Pendiente |
| Diapositivas | Pendientes |
| Video | Pendiente |

## Limitaciones actuales

- No se han generado datos.
- No se han instalado dependencias.
- No se ha ejecutado código.
- No se han calculado indicadores.
- No se ha conectado un modelo de IA.
- No existen resultados del prototipo.
- No existen métricas reales de ahorro, precisión o mejora.
- La formulación definitiva del problema continúa pendiente.

## Documentación del proyecto

La carpeta `docs/` contendrá:

- Arquitectura.
- Diccionario de datos.
- Reglas de calidad.
- Matriz de riesgos.
- Biblioteca de prompts.
- Registro de cambios.

## Control de cambios

Los cambios relevantes deberán registrarse en:

```text
docs/changelog.md
```

Cada registro incluirá:

- Fecha.
- Versión.
- Cambio.
- Motivo.
- Archivos afectados.
- Validación realizada.
- Resultado obtenido.
- Próximo paso.

## Próximo paso

Configurar los archivos fundamentales del proyecto antes de crear el entorno virtual e instalar dependencias.
