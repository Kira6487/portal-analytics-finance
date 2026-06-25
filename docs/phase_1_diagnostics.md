# Fase 1 — Diagnóstico SAP B1

## 1. Objetivo

Validar que la base SAP Business One de pruebas contiene datos suficientes y
estructurados para continuar con un motor financiero histórico y, más adelante,
con proyecciones explicables.

## 2. Stack

Python, FastAPI, Uvicorn, SQLAlchemy, pyodbc, pandas, NumPy, scikit-learn,
statsmodels y python-dotenv. En esta fase scikit-learn y statsmodels quedan
disponibles, pero no se entrenan modelos.

## 3. Conexión

La conexión usa SQLAlchemy con `mssql+pyodbc`, timeout de 10 segundos,
`pool_pre_ping` y `TrustServerCertificate=yes`. La configuración acepta variables
de entorno y conserva los valores del proyecto logístico como defaults locales.

**Seguridad:** las credenciales por defecto se permiten únicamente por tratarse
de una demo local. Producción debe usar secretos, una cuenta SQL de solo lectura,
rotación de credenciales y restricciones de red.

## 4. Endpoints

- `GET /api/diagnostics/health`: ejecuta `SELECT 1`, informa servidor y base.
- `GET /api/diagnostics/sap-data`: ejecuta el diagnóstico completo sin modificar
  SAP.

## 5. Tablas validadas

OACT, OJDT, JDT1, OCRD, OINV, INV1, ORIN, RIN1, OPCH, PCH1, ORPC, RPC1,
ORCT, RCT2, OVPM, VPM2, OCTG, OPRC, OBGT y BGT1.

## 6. Diagnóstico contable

Calcula rango de fechas, asientos, líneas, cuentas, meses, años, débitos,
créditos y diferencia. Advierte sobre meses vacíos y posibles descuadres.

## 7. Cuentas por cobrar

Revisa facturas, documentos abiertos, saldo pendiente, clientes, vencimientos y
existencia de detalle de pagos recibidos.

## 8. Cuentas por pagar

Revisa facturas de proveedor, documentos abiertos, saldo pendiente, proveedores,
vencimientos e historial de pagos efectuados.

## 9. Dimensiones

Detecta `OcrCode` a `OcrCode5`, cuenta registros de OPRC y valida qué campos
tienen movimientos.

## 10. Presupuesto

Busca OBGT y BGT1 y cuenta registros. Si no encuentra datos, recomienda construir
un presupuesto simulado únicamente para la futura demo.

## 11. Viabilidad predictiva

La evaluación inicial usa meses disponibles, continuidad mensual y volatilidad:

- Menos de 12 meses: baja.
- 12 a 24 meses: media.
- Más de 24 meses: alta.

Esta clasificación no reemplaza backtesting, MAPE/MAE ni validación contable.

## 12. Limitaciones

La ejecución real del 25 de junio de 2026 detectó:

- La clasificación de cuentas es preliminar y debe validarse con Contabilidad.
- OBGT y BGT1 existen, pero no contienen registros presupuestales.
- Los movimientos mensuales agregados presentan alta volatilidad; la confianza
  no debe asumirse alta solo por disponer de una serie extensa.
- Real vs Presupuesto requerirá presupuesto simulado en la demo, salvo que se
  cargue un presupuesto real.

## 13. Decisiones técnicas

- Consultas exclusivamente `SELECT`.
- Fallos por tabla o consulta se capturan y se reportan sin derribar el endpoint.
- La clasificación de cuentas combina `ActType` con palabras clave de
  `AcctName`; se considera preliminar.
- No se construyó frontend ni se entrenaron modelos, respetando el alcance.

## 14. Recomendación para Fase 2

Continuar con el motor financiero histórico solo después de validar con
Contabilidad la clasificación de ingresos, costos y gastos, y de revisar las
limitaciones detectadas en la ejecución real.

## 15. Estado de ejecución

Diagnóstico ejecutado exitosamente el **25 de junio de 2026** contra
`CFR-I7-1 / SBO_MEDINET_MIGRACION`:

| Área | Resultado |
|---|---|
| Conexión | Exitosa con ODBC Driver 17 for SQL Server |
| Tablas principales | 20 de 20 detectadas |
| Rango contable | 2019-05-01 a 2025-12-23 |
| Cobertura | 80 meses calendario y 80 meses con movimientos |
| Asientos / líneas | 345,170 / 1,037,336 |
| Cuentas contables | 2,133 |
| Débitos / créditos | 4,918,576,879.78 / 4,918,576,879.78 |
| Descuadre | 0.00 |
| Cuentas de ingreso / costo / gasto | 150 / 36 / 314, clasificación preliminar |
| CxC | 16,326 facturas; 239 abiertas; saldo 2,200,229.33 |
| CxP | 36,249 facturas; 263 abiertas; saldo 2,287,604.08 |
| Dimensiones | 87 centros; OcrCode2 a OcrCode5 con movimientos |
| Presupuesto | Tablas presentes, 0 registros |
| Readiness predictivo | Alto por cobertura, condicionado por volatilidad |
| Estado general | Parcial |

Los endpoints `/api/diagnostics/health` y `/api/diagnostics/sap-data` respondieron
HTTP 200 con `status=ok`. La conclusión es que existe base suficiente para
continuar a Fase 2, pero el mapeo del Estado de Resultados y la estrategia de
presupuesto deben aprobarse antes de construir cálculos financieros.
