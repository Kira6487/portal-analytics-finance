# Fase 7 - Balance proyectado simplificado

## 1. Objetivo

Construir una vista gerencial de posicion financiera futura que integre Balance
historico, flujo de caja proyectado, CxC predictiva, CxP predictiva, forecast de
ingresos/costos, escenarios, ratios, alertas, explicaciones y recomendaciones.

## 2. Naturaleza gerencial

El Balance proyectado simplificado no reemplaza el Balance oficial de SAP, no
crea asientos contables, no modifica SAP y no debe usarse como reporte contable
formal. Depende de supuestos de cobranza, pagos, forecast y calidad de datos.
Debe validarse con Contabilidad y Tesoreria.

## 3. Datos usados

Se reutilizan servicios internos de fases previas:

- `balance_summary` de Fase 2.
- `weekly_projection` y escenarios de Fase 4.
- Dataset CxC predictiva de Fase 5.
- Dataset CxP predictiva de Fase 6.
- Forecast de Estado de Resultados de Fase 3.

No se duplican consultas principales ni se escribe informacion en SAP.

## 4. Moneda oficial

La moneda oficial de la demo es `SOL` con simbolo `S/`. Los importes gerenciales
usan valores locales SAP. Se conserva la advertencia de que documentos en moneda
fuente distinta de SOL requieren politica FX productiva antes de produccion.

## 5. Caja proyectada

La caja proyectada se toma de la proyeccion semanal de Fase 4:

`projected_cash = opening_cash + cumulative_projected_net_cashflow`

Si la caja inicial es detectada por Fase 4 se usa esa fuente. Si el usuario envia
`opening_cash`, se respeta como parametro. Si SQL/ODBC falla, el endpoint devuelve
estructura controlada con caja cero o el parametro enviado, mas warnings.

## 6. CxC proyectada

La CxC proyectada parte del monto abierto de CxC predictiva y resta cobros
esperados acumulados por semana. Nunca se devuelve negativa:

`projected_ar = max(0, current_open_ar - expected_collections_until_period)`

## 7. CxP proyectada

La CxP proyectada parte del monto abierto de CxP predictiva y resta pagos
esperados acumulados por semana. Nunca se devuelve negativa:

`projected_ap = max(0, current_open_ap - expected_payments_until_period)`

## 8. Resultado proyectado

Se usa el forecast de margen bruto como aproximacion limitada del resultado
proyectado. Si en una fase futura existe utilidad operativa o utilidad neta
proyectada, debe reemplazar esta aproximacion.

## 9. Otros saldos

Para esta demo:

- Otros activos permanecen constantes.
- Otros pasivos permanecen constantes.
- Patrimonio base permanece constante.
- Patrimonio estimado se ajusta con el resultado proyectado proxy.

Estos saldos no estan modelados dinamicamente.

## 10. Ratios calculados

- Capital de trabajo: `cash + ar - ap`.
- Caja / CxP.
- CxC / CxP.
- Pasivos / activos.
- Liquidez gerencial: `(cash + ar) / ap`.

Las divisiones por cero devuelven `null`.

## 11. Estados de liquidez

- `healthy`: caja positiva y liquidez gerencial >= 1.2.
- `watch`: caja positiva y liquidez gerencial entre 1.0 y 1.2, o caja positiva
  sin ratio calculable.
- `stressed`: caja no negativa y liquidez gerencial menor a 1.0.
- `critical`: caja negativa.

## 12. Escenarios

- `base`: usa fechas estimadas normales.
- `optimistic`: adelanta cobros y mantiene pagos normales segun Fase 4.
- `pessimistic`: retrasa cobros y mantiene presion de pagos vencidos.

El endpoint de escenarios compara caja final, caja minima, capital de trabajo,
CxC final, CxP final, semanas deficitarias y estado de liquidez.

## 13. Alertas

Alertas implementadas:

- Caja proyectada negativa.
- Capital de trabajo negativo.
- CxP superior a caja mas CxC.
- Escenario pesimista con deficit.
- Forecast con confianza baja.
- Politica FX pendiente.
- Diferencia de cuadre gerencial.
- Caja inicial no validada.

## 14. Explicaciones automaticas

Las explicaciones son reglas deterministicas. Describen fuentes usadas, logica de
caja, CxC, CxP, escenarios, naturaleza gerencial, SOL y fallback cuando SQL/ODBC
no entrega datos.

## 15. Recomendaciones automaticas

El modulo recomienda priorizar cobranza ante caja negativa, revisar pagos
urgentes y revisables, evaluar calendario de pagos, no usar forecast de baja
confianza como unico criterio, validar caja inicial con Tesoreria y definir
politica FX productiva.

## 16. Confianza

- Alta: conexion SAP funcionando, caja detectada o enviada, alta cobertura
  historica, moneda oficial definida.
- Media: servicios CxC/CxP funcionando, caja no validada o componentes
  constantes.
- Baja: SQL/ODBC falla, caja no detectada, forecast de baja confianza, muchos
  supuestos o politica FX pendiente.

El resumen ejecutivo incluye `confidence_reasons`.

## 17. Limitaciones

- Vista gerencial, no Balance oficial.
- No crea asientos contables.
- No modifica SAP.
- Depende de supuestos de cobranza, pagos y forecast.
- Debe validarse con Contabilidad y Tesoreria.
- Otros activos, otros pasivos y patrimonio se mantienen constantes.
- Documentos en moneda fuente distinta de SOL requieren politica FX productiva.

## 18. Endpoints creados

- `GET /api/balance-projection/dataset`
- `GET /api/balance-projection/weekly`
- `GET /api/balance-projection/scenarios`
- `GET /api/balance-projection/drivers`
- `GET /api/balance-projection/executive-summary`

Ejemplos:

- `/api/balance-projection/weekly?horizon_weeks=13&scenario=base`
- `/api/balance-projection/weekly?horizon_weeks=13&scenario=base&opening_cash=1000000`
- `/api/balance-projection/scenarios?horizon_weeks=13&opening_cash=1000000`

## 19. Resultados principales obtenidos

Conectividad SQL/ODBC actual: falla con error de cifrado/conexion del driver
ODBC 17. Se agrego `DB_ENCRYPT=no` configurable, pero el entorno actual sigue
devolviendo `Encryption not supported on the client` y `Client unable to
establish connection`.

Validacion manual:

- Los 5 endpoints nuevos responden HTTP 200.
- Sin `opening_cash`, la caja inicial usada es `fallback_zero` y la caja final
  proyectada queda en S/ 0.00 por falta de datos reales.
- Con `opening_cash=1000000`, la caja inicial usada es `parameter`, caja final
  S/ 1,000,000.00, capital de trabajo final S/ 1,000,000.00 y liquidez gerencial
  `null` porque CxP real no estuvo disponible.
- Escenario base y pesimista quedan iguales durante la falla SQL porque no hay
  documentos ni flujo real para diferenciar escenarios.
- Suite completa: `50 passed`.

## 20. Estado de conectividad SQL/ODBC

La conexion debe resolverse antes de usar metricas proyectadas para decisiones.
El backend conserva errores controlados y warnings claros; no inventa saldos SAP,
documentos, cobros ni pagos.

## 21. Recomendacion para Fase 8

Antes del frontend final, resolver conectividad SQL/ODBC y validar la caja
inicial con Tesoreria. Luego avanzar a rentabilidad predictiva por dimensiones o
a una primera interfaz exploratoria que consuma endpoints ya estables, sin
automatizaciones ni escritura en SAP.
