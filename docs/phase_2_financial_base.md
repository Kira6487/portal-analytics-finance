# Fase 2 — Motor financiero base histórico

## 1. Objetivo

Construir una capa financiera de solo lectura sobre SAP Business One para
consultar historia contable, documentos abiertos, flujo de caja base,
rentabilidad por dimensión y un presupuesto simulado. No se entrenan modelos ni
se generan forecasts.

## 2. Datos usados

La validación se ejecutó el 25 de junio de 2026 contra
`CFR-I7-1 / SBO_MEDINET_MIGRACION`, con historia entre 2019-05-01 y 2025-12-23.
Se usan OACT, OJDT, JDT1, OINV, OPCH, ORCT, OVPM y OPRC mediante consultas
`SELECT`.

## 3. Mapeo contable preliminar

`financial_mapping.py` clasifica cuentas usando:

- overrides por cuenta o prefijo;
- `GroupMask` y `ActType`;
- `FormatCode`, que contiene el código contable visible;
- palabras clave de `AcctName`.

El archivo `backend/config/account_mapping_overrides.json` permite corregir el
mapeo sin modificar código. Las cuentas internas `_SYS...` se muestran mediante
su `FormatCode`.

La validación detectó 985 cuentas contabilizables: 972 clasificadas y 13 no
clasificadas. Las 13 corresponden a clase 8:

- 80, 81, 82, 83, 84 y 85: saldos intermedios de gestión;
- 87 y 88: participaciones e impuesto;
- 89: utilidad, pérdida y resultado del ejercicio.

Estas cuentas se excluyen del Estado de Resultados para evitar doble conteo con
las clases 6 y 7. Contabilidad debe decidir su tratamiento definitivo.

## 4. Advertencia de clasificación

La clasificación es útil para una demo y análisis exploratorio, pero no es un
plan de cuentas aprobado. En especial:

- GroupMask 5 se trata preliminarmente como costo de ventas.
- GroupMask 6 se divide entre administración, ventas, financiero y operativo.
- GroupMask 7 se trata como otros ingresos u otros gastos.
- GroupMask 8 se excluye como cuenta de cierre/resultado.

## 5. Lógica de signos

- Ingresos, otros ingresos, pasivos y patrimonio: `crédito - débito`.
- Activos, costos y gastos: `débito - crédito`.

Así los ingresos, costos y gastos habituales se presentan como importes
positivos. El endpoint advierte si detecta ingresos netos negativos.

## 6. Endpoints

- `GET /api/financial/metadata`
- `GET /api/financial/income-statement`
- `GET /api/financial/income-statement-vs-budget`
- `GET /api/financial/balance-summary`
- `GET /api/financial/receivables/open`
- `GET /api/financial/payables/open`
- `GET /api/financial/cashflow/base`
- `GET /api/financial/profitability/dimensions`
- `GET /api/financial/budget/simulated`

Los endpoints de diagnóstico de Fase 1 continúan activos.

## 7. Presupuesto simulado

Admite `prior_year`, `historical_average` y `rolling_12m`, con crecimiento
configurable (5% por defecto). Genera 12 meses y una distribución preliminar por
`OcrCode2`. Siempre se identifica como demo no oficial.

## 8. Cuentas por cobrar y pagar

Se consultan documentos actualmente abiertos, saldo, vencimiento, aging y reglas
de riesgo/prioridad. Al 2025-12-23 se observaron:

- CxC: 238 documentos con saldo, 72 clientes y 2,200,229.33 abiertos.
- CxP: 262 documentos con saldo, 105 proveedores y 2,287,604.08 abiertos.

SAP conserva el estado actual del documento; un filtro histórico no reconstruye
facturas que hoy ya están cerradas.

## 9. Flujo de caja base

Usa ORCT y OVPM para cobros/pagos históricos, y vencimientos de documentos
abiertos para movimientos esperados. No calcula caja inicial ni saldo bancario
conciliado. Para 2025 se validó un flujo neto combinado de -4,317,638.81, cifra
exploratoria sujeta a moneda y conciliación.

## 10. Rentabilidad por dimensiones

JDT1 contiene `OcrCode2` a `OcrCode5`; no contiene `OcrCode`. Para 2025,
`OcrCode2` devolvió siete agrupaciones con movimiento. El nombre se obtiene de
OPRC cuando existe coincidencia.

## 11. Balance gerencial

Al 2025-12-23:

- Activos: 11,987,080.51
- Pasivos: 7,315,766.90
- Patrimonio: 4,016,458.18
- Resultado estimado: 654,855.43
- Diferencia de cuadre: 0.00
- Deuda/activo: 0.6103

No se separa corriente/no corriente; por ello no se publican capital de trabajo
ni liquidez corriente. No reemplaza el Balance oficial de SAP.

## 12. Limitaciones

- Mapeo aún no aprobado por Contabilidad.
- Importes en varias monedas se agregan según valores locales de SAP; falta una
  política explícita de moneda de reporte.
- No hay snapshot histórico de documentos abiertos.
- Caja inicial y cuentas bancarias conciliadas no están determinadas.
- El presupuesto es simulado.
- La alta volatilidad detectada en Fase 1 sigue vigente.

## 13. Decisiones técnicas

- SQL parametrizado y dimensiones limitadas por whitelist.
- Sin escrituras en SAP.
- Servicios separados para estados, documentos, caja, dimensiones y presupuesto.
- Respuestas vacías incluyen warnings en lugar de errores no controlados.
- Overrides JSON preparados para validación contable futura.

La validación final ejecutó los nueve endpoints financieros y los dos endpoints
de diagnóstico contra SAP real, todos con HTTP 200. La suite automatizada terminó
con `7 passed`; permanece una advertencia de deprecación de TestClient en la
combinación actual de FastAPI/Starlette, sin impacto funcional.

## 14. Recomendación para Fase 3

Antes del primer forecast, validar una muestra del Estado de Resultados con
Contabilidad, definir moneda funcional/de reporte y aprobar el tratamiento de
clases 5, 6 y 8. Después, el primer módulo predictivo recomendado es ingresos y
margen bruto mensual con backtesting de modelos simples.
