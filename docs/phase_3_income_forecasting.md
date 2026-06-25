# Fase 3 — Forecast de ingresos y margen bruto

## 1. Objetivo

Validar un primer motor predictivo financiero explicable para ingresos, costo de
ventas, margen bruto y margen bruto porcentual. La salida es gerencial y no
constituye un estado financiero oficial.

## 2. Datos usados

La serie mensual reutiliza el mapeo y los signos de Fase 2. Contiene 80 meses,
desde 2019-05 hasta 2025-12. La fecha máxima de movimiento operativo de ingresos
y costo detectada es 2025-12-19.

Se excluyen:

- cuentas clase 8, para evitar doble conteo;
- asientos `OJDT.TransType = -3`, identificados como cierres de período.

Esta última limpieza fue necesaria porque el cierre del 31 de diciembre de 2024
revertía aproximadamente 17 millones de ingresos y 9.7 millones de costos,
distorsionando el dataset sin representar operación real.

## 3. Series pronosticadas

Se pronostican por separado:

- `revenue`;
- `cost_of_sales`.

Después se calculan:

- `gross_profit = revenue - cost_of_sales`;
- `gross_margin_pct = gross_profit / revenue`.

Los meses con ingreso cero generan margen porcentual `null`.

## 4. Modelos implementados

- `naive_last_value`
- `seasonal_naive_12`
- `moving_average_3`
- `moving_average_6`
- `holt_winters`
- `calendar_linear_regression`

Todos implementan una interfaz común `fit/predict`. Los fallos individuales se
capturan y no derriban el endpoint.

## 5. Backtesting

La validación principal reserva los últimos seis meses, entrena con los 74 meses
anteriores y pronostica el bloque completo de prueba. El periodo se puede
configurar entre 1 y 24 meses.

## 6. Selección del modelo

Se elige el menor MAPE válido. Si MAPE no puede calcularse, se usa MAE. Si todos
los modelos fallan, el fallback es `naive_last_value`.

## 7. Métricas

Resultados reales con holdout de seis meses:

| Serie | Modelo | MAE | MAPE | RMSE |
|---|---|---:|---:|---:|
| Ingresos | Naive | 599,048.40 | 54.84% | 669,802.69 |
| Ingresos | Seasonal Naive 12 | **353,467.97** | **33.03%** | 468,028.62 |
| Ingresos | Media móvil 3 | 505,966.31 | 46.56% | 570,313.23 |
| Ingresos | Media móvil 6 | 523,451.03 | 48.26% | 593,412.65 |
| Ingresos | Holt-Winters | 597,610.96 | 54.75% | 678,146.51 |
| Ingresos | Regresión calendario | 400,529.71 | 35.73% | **435,770.97** |
| Costo | Naive | 354,220.94 | 55.65% | 404,766.22 |
| Costo | Seasonal Naive 12 | **189,684.98** | **30.29%** | 264,830.26 |
| Costo | Media móvil 3 | 298,583.23 | 47.55% | 350,080.77 |
| Costo | Media móvil 6 | 313,492.00 | 49.67% | 363,760.47 |
| Costo | Holt-Winters | 375,282.49 | 58.99% | 430,101.32 |
| Costo | Regresión calendario | 204,511.29 | 31.53% | **248,314.75** |

Ganadores por criterio MAPE:

- Ingresos: `seasonal_naive_12`.
- Costo de ventas: `seasonal_naive_12`.

## 8. Confianza

Ambas series reciben confianza **baja**:

- ingresos: MAPE 33.03%, CV 0.54;
- costo: MAPE 30.29%, CV 0.55.

La cobertura de 80 meses es favorable, pero no compensa errores superiores a
25% ni la volatilidad observada.

## 9. Rangos

El rango usa `forecast × (1 ± MAPE)`, limitado a cero para ingresos y costos. Si
MAPE no está disponible se usan márgenes de 10%, 20% o 35% según confianza.
Estos rangos son heurísticos, no intervalos estadísticos formales.

## 10. Presupuesto simulado

Para cada mes futuro se toma el mismo mes del año anterior y se aplica 5% de
crecimiento. Con Seasonal Naive como ganador, el forecast queda 4.76% por debajo
de ese presupuesto por construcción matemática. Esto debe entenderse como una
comparación demo, no como evidencia de deterioro comercial.

## 11. Explicaciones

Las explicaciones son determinísticas e informan modelo, error, cálculo de
margen, meses bajo presupuesto y naturaleza simulada del presupuesto.

## 12. Recomendaciones

Las reglas recomiendan revisión comercial, análisis de costos, inspección de
atípicos, validación manual cuando la confianza es baja y carga de presupuesto
oficial.

## 13. Endpoints

- `GET /api/forecasting/income-statement/dataset`
- `GET /api/forecasting/income-statement/backtest`
- `GET /api/forecasting/income-statement/forecast`
- `GET /api/forecasting/income-statement/executive-summary`

Los horizontes admitidos son 3, 6 y 12 meses.

## 14. Limitaciones y resultados

- Mapeo contable preliminar.
- Moneda oficial de reporte pendiente.
- Presupuesto simulado.
- Alta variabilidad y MAPE superior a 30%.
- Diciembre de 2025 contiene movimientos hasta el día 19 para estas series.
- No se modelan variables comerciales externas ni eventos extraordinarios.
- La proyección no debe utilizarse sin revisión gerencial.

Los cuatro endpoints predictivos, los horizontes 3/6/12 y endpoints de Fases 1 y
2 respondieron HTTP 200. La suite completa terminó con `16 passed`.

## 15. Recomendación para Fase 4

Antes de proyectar flujo de caja, conviene revisar los meses atípicos de ingresos
y costo, definir moneda de reporte y validar el presupuesto con Gerencia. Para
Fase 4 se recomienda combinar CxC/CxP abiertas, vencimientos e historial de pago
mediante reglas explicables, sin depender únicamente de series temporales.
