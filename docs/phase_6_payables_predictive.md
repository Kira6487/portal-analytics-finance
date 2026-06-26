# Fase 6 - Cuentas por pagar predictivas

## 1. Objetivo

Construir un modulo de CxP predictiva para analizar facturas abiertas de
proveedores, estimar prioridad de pago, riesgo operativo/financiero, presion
sobre caja, fecha sugerida y recomendaciones gerenciales. El modulo es de solo
lectura, no modifica SAP y no programa pagos.

## 2. Moneda oficial

La moneda oficial de reporte de la demo es:

- Codigo: `SOL`
- Simbolo: `S/`
- Nombre: Soles
- Politica: valores locales SAP sin conversion FX productiva

Todas las respuestas gerenciales devuelven `currency: SOL` y
`currency_symbol: S/`. Se conserva `source_currency` para identificar documentos
originados en USD, YEN u otra moneda. Si hay documentos no SOL, se emite warning
de validacion FX productiva.

## 3. Datos usados

Se reutilizan CxP abiertas de Fase 2, comportamiento historico de proveedores de
Fase 4, documentos proyectables, proyeccion semanal de caja a 13 semanas,
escenarios `base`, `optimistic` y `pessimistic`, y configuracion SOL de Fase 5.

## 4. Score de prioridad por factura

El score va de 0 a 100 y combina dias vencidos, proximidad de vencimiento, monto
pendiente frente al promedio, proveedor concentrador, semana deficitaria, falta
de historial, recurrencia del proveedor, antiguedad del documento y presion
acumulada.

Clasificacion:

- 0-24: low
- 25-49: medium
- 50-74: high
- 75-100: urgent

## 5. Riesgo por factura

El riesgo mide impacto operativo/financiero por no atender el pago. No es riesgo
crediticio. Considera vencimiento, monto, concentracion, semana deficitaria,
falta de historial, documentos 90+, moneda fuente distinta de SOL sin politica
FX productiva y presion acumulada.

Clasificacion:

- 0-24: low
- 25-49: medium
- 50-74: high
- 75-100: critical

## 6. Score por proveedor

El endpoint de proveedores agrupa facturas por `card_code` y calcula monto
abierto, documentos vencidos, scores ponderados por monto, nivel de prioridad,
nivel de riesgo, comportamiento de pago, montos venciendo a 7/30/60/90 dias,
concentracion, presion de caja y confianza.

## 7. Fechas estimadas y recomendadas

La fecha estimada usa vencimiento, mediana historica de dias de pago, escenario,
estado actual del documento y semana de caja. En base se calcula como
vencimiento mas mediana historica; sin historial se usa el vencimiento. Los
documentos vencidos no se proyectan antes de la fecha base.

La fecha recomendada es una sugerencia gerencial. Si el documento esta vencido
se recomienda gestion inmediata; si vence en siete dias se recomienda el
vencimiento; si cae en deficit se marca para revision, no para movimiento
automatico.

## 8. Pagos revisables o postergables

Un pago puede marcarse como revisable si no esta vencido, no vence dentro de los
proximos siete dias, tiene prioridad baja o media, no tiene riesgo critico, cae
en una semana deficitaria y no pertenece a un proveedor altamente concentrador.
La postergacion exige validacion de Tesoreria y negociacion con el proveedor.

## 9. Concentracion

La concentracion muestra top 10 proveedores por monto abierto, porcentaje sobre
CxP total, monto urgente, monto vencido, riesgo de dependencia y presion semanal.
El riesgo global se define con la concentracion top 5.

## 10. Alertas

Se generan alertas por documentos vencidos criticos, proveedores con mas del 20%
de CxP, alto monto vencido, pagos en semanas deficitarias, proveedores sin
historial con monto relevante, varios documentos vencidos del mismo proveedor,
moneda fuente distinta de SOL y potencial deficit por pagos concentrados.

## 11. Explicaciones automaticas

Las explicaciones son deterministicas. Describen los factores del score, la
fecha estimada, la condicion de pago revisable, la moneda oficial SOL y la
restriccion de que las recomendaciones no modifican SAP ni programan pagos.

## 12. Recomendaciones automaticas

Las recomendaciones cubren revision de documentos urgentes, calendario de pagos
en semanas deficitarias, seguimiento a proveedores concentradores, negociacion
de plazos, validacion FX, validacion manual sin historial y revision de cobranza
prioritaria cuando existan pagos criticos con caja insuficiente.

## 13. Confianza

- Alta: mas de 10 documentos historicos pagados, vencimiento valido y fuente SOL.
- Media: entre 3 y 10 documentos historicos y vencimiento valido.
- Baja: menos de 3 documentos, falta de historial, falta de vencimiento, moneda
  fuente distinta de SOL sin conversion productiva o comportamiento volatil.

Cada documento y proveedor incluye razones de confianza.

## 14. Endpoints creados

- `GET /api/payables-predictive/dataset`
- `GET /api/payables-predictive/vendors`
- `GET /api/payables-predictive/priorities`
- `GET /api/payables-predictive/deferrable`
- `GET /api/payables-predictive/concentration`
- `GET /api/payables-predictive/executive-summary`

Filtros principales: `as_of_date`, `vendor`, `priority`, `risk`, `min_amount`,
`days_overdue_min`, `scenario`, `include_closed` y `limit` segun endpoint.

## 15. Limitaciones

- La moneda oficial de demo es SOL.
- Documentos en moneda extranjera pueden requerir conversion futura.
- La fecha recomendada no programa pagos automaticamente.
- La clasificacion de prioridad es una regla gerencial inicial.
- Depende de que SAP tenga documentos, pagos y conciliaciones correctamente registrados.
- No reemplaza criterio de Tesoreria ni Contabilidad.
- No modifica SAP.
- No debe usarse como instruccion automatica de pago.

## 16. Resultados principales obtenidos

El modulo entrega dataset por factura, score de prioridad, score de riesgo,
score por proveedor, fecha estimada, fecha recomendada, priorizacion, pagos
revisables, concentracion, resumen ejecutivo, alertas, explicaciones y
recomendaciones. Los resultados cuantitativos se obtienen desde
`/api/payables-predictive/dataset`, `/priorities`, `/deferrable` y `/vendors`
con la fecha base disponible en SAP.

Resultado tecnico de esta entrega:

- 6 endpoints nuevos registrados.
- Filtros de prioridad, riesgo y escenario validados.
- Suite completa: `41 passed`.
- Validacion manual de endpoints: HTTP 200 con manejo controlado de error.
- En esta sesion no fue posible recalcular metricas reales de CxP porque la
  conexion SQL Server/ODBC local devolvio error de cifrado/conectividad.

## 17. Recomendacion para Fase 7

Construir Balance proyectado simplificado y posicion financiera futura,
integrando CxC predictiva, CxP predictiva y flujo de caja proyectado. No avanzar
a automatizacion de pagos ni frontend final sin validar antes politica FX,
criterios de Tesoreria y reglas contables.
