## NovaRetail Financial GenAI v0.1.0

Primera versión funcional del proyecto académico NovaRetail Financial GenAI.

### Funcionalidades incluidas

- Generación reproducible de datos completamente sintéticos.
- Catálogos de 120 productos y 4.000 clientes.
- Generación de 23.706 líneas correspondientes a 18.072 pedidos.
- Inventario mensual, devoluciones y métricas de marketing.
- Estado de resultados, balance general y flujo de efectivo para 36 periodos.
- Presupuesto mensual con ocho categorías.
- Exportación profesional a un libro Excel con 12 hojas.
- Validaciones estructurales, de calidad, contables y relacionales.
- Scripts independientes para generación y validación.
- Alertas de valores atípicos mediante el método IQR.
- Suite automatizada con 357 pruebas aprobadas.

### Comandos principales

```powershell
python scripts\generate_data.py
python scripts\validate_data.py
python -m pytest tests -q