# Fase 5 — Cuentas por cobrar predictivas

## 1. Objetivo

Analizar cada factura abierta, estimar su fecha de cobro, riesgo, prioridad e
impacto sobre el flujo de caja. El módulo usa reglas explicables y no modifica
SAP.

## 2. Moneda oficial

La moneda oficial de reporte de la demo es:

- Código: `SOL`
- Símbolo: `S/`
- Nombre: Soles
- Política: valores locales SAP sin conversión FX productiva

Los importes gerenciales se presentan en SOL. Se conserva `source_currency` para
identificar documentos originados en USD, YEN u otra moneda. En la cartera
actual, 146 de 238 documentos tienen moneda fuente distinta de SOL.

## 3. Datos usados

Se reutilizan CxC abiertas, aging, comportamiento histórico de clientes, fechas
estimadas y semanas de déficit de Fases 2 y 4. La fecha base automática es
2025-12-23.

## 4. Score por factura

El score de 0 a 100 combina:

- días vencidos;
- monto frente al promedio;
- comportamiento histórico;
- concentración del cliente;
- falta de historial;
- antigüedad;
- coincidencia con semana de déficit.

Clasificación:

- 0–24: low
- 25–49: medium
- 50–74: high
- 75–100: critical

Resultado real:

| Riesgo | Documentos | Monto |
|---|---:|---:|
| Low | 3 | incluido en cartera |
| Medium | 81 | incluido en cartera |
| High | 88 | S/ 850,439.48 |
| Critical | 66 | S/ 570,489.79 |

## 5. Score por cliente

Se calcula el promedio de score ponderado por monto abierto. También se informa
aging, concentración, comportamiento, confianza y cobros estimados a 30/60/90
días. Se detectaron 72 clientes con cartera abierta.

Los primeros clientes por score ponderado son:

- RETINORT S.A.C.: S/ 32,024.00, score 100.
- INVERCONSULT S.A.: S/ 10,865.58, score 100.
- INVERSIONES MEDICAS Y TECNOLOGICAS E.I.R.L.: S/ 9,159.11, score 100.
- GRUPO OFTALMIKA S.A.C.: S/ 5,176.00, score 100.
- CENTRO VISUAL INTEGRAL S.A.C.: S/ 4,094.54, score 100.

## 6. Fecha estimada

Reutiliza las reglas de Fase 4:

- base: vencimiento + mediana histórica;
- sin historial: vencimiento + 7 días;
- optimista: siete días antes;
- pesimista: quince días después.

Las fechas vencidas no se proyectan antes de la fecha base.

## 7. Priorización

El priority score pondera riesgo, monto, vencimiento, concentración, falta de
historial e impacto en déficit.

Los cinco primeros documentos urgentes son:

- 23100791 — RETINORT S.A.C. — S/ 32,024.00.
- 26100560 — JUNIOR INVESTMENT E.I.R.L. — S/ 33,397.38.
- 26100666 — JUNIOR INVESTMENT E.I.R.L. — S/ 21,306.53.
- 26100594 — JUNIOR INVESTMENT E.I.R.L. — S/ 48,472.18.
- 26100599 — SEGURO SOCIAL DE SALUD — S/ 30,705.00.

## 8. Concentración

- Cartera total: S/ 2,200,229.33.
- Top 5: 52.67%.
- Top 10: 71.33%.
- Riesgo de concentración: medio.

## 9. Alertas

Se generan alertas por documentos 90+, concentración superior a 20%, múltiples
documentos vencidos, monto de riesgo alto, dependencia de semanas deficitarias y
fechas fuera del horizonte de 13 semanas.

## 10. Explicaciones

Las explicaciones son determinísticas y describen los factores del score, fecha
estimada, concentración, cobertura histórica y moneda SOL.

## 11. Recomendaciones

Incluyen gestión inmediata de documentos críticos, seguimiento directo a
clientes concentradores, priorización antes de semanas deficitarias, validación
manual sin historial, revisión contable/legal de documentos 90+ y validación FX.

## 12. Confianza

- Alta: más de 10 documentos históricos, vencimiento válido y fuente SOL.
- Media: entre 3 y 10 documentos históricos y fuente SOL.
- Baja: menos de 3 documentos, falta de historial o moneda fuente distinta de
  SOL sin conversión productiva.

## 13. Endpoints

- `GET /api/receivables-predictive/dataset`
- `GET /api/receivables-predictive/customers`
- `GET /api/receivables-predictive/priorities`
- `GET /api/receivables-predictive/concentration`
- `GET /api/receivables-predictive/executive-summary`

Los cinco endpoints, filtros principales y endpoints representativos de Fases
1–4 respondieron HTTP 200.

## 14. Limitaciones

- Los importes usan valores locales SAP reportados en SOL.
- Documentos fuente no SOL requieren política FX productiva.
- La fecha estimada no garantiza cobro.
- El score no es una calificación crediticia formal.
- Depende de conciliación y calidad de datos SAP.
- No reemplaza criterio contable o gestión de cobranza.
- No modifica SAP.

## 15. Resultados principales

- 238 documentos.
- 72 clientes.
- S/ 2,200,229.33 de cartera.
- S/ 850,439.48 en riesgo alto por factura.
- S/ 570,489.79 en riesgo crítico por factura.
- 61 documentos urgentes.
- Suite completa: `32 passed`.

## 16. Decisiones técnicas

- Se reutilizan servicios de Fases 2 y 4.
- Reglas acotadas entre 0 y 100.
- Filtros y escenarios validados.
- Respuestas incluyen SOL, S/, moneda fuente, limitations y warnings.
- Consultas exclusivamente de lectura.

## 17. Recomendación para Fase 6

Construir CxP predictiva y priorización de pagos, reutilizando comportamiento de
proveedores, vencimientos, presión semanal y caja disponible. Antes de producción
debe aprobarse la política de conversión a SOL.
