# Fase 4 — Flujo de caja proyectado documental

## 1. Objetivo

Construir una proyección semanal de caja a 13 semanas basada en documentos
abiertos, comportamiento histórico y escenarios explicables. No se entrenan
modelos avanzados ni se escribe información en SAP.

## 2. Datos usados

- OINV, RCT2 y ORCT para CxC e historial de cobranza.
- OPCH, VPM2 y OVPM para CxP e historial de pagos.
- OACT, JDT1 y OJDT para estimar caja inicial.
- Fecha base automática: 2025-12-23, máxima fecha disponible en SAP.

Se detectaron 238 documentos CxC y 262 documentos CxP proyectables.

## 3. Lógica de CxC

`RCT2.DocEntry` se vincula con `OINV.DocEntry`, mientras `RCT2.DocNum` se
vincula con `ORCT.DocEntry`. Para cada factura se utiliza la última fecha de pago
aplicada. El atraso es la diferencia entre esa fecha y el vencimiento.

Si el cliente tiene historial:

`fecha estimada = vencimiento + mediana de atraso`

Si no tiene historial se usan siete días en el escenario base.

## 4. Lógica de CxP

`VPM2.DocEntry` se vincula con `OPCH.DocEntry` y `VPM2.DocNum` con
`OVPM.DocEntry`. La fecha de pago histórica se compara con el vencimiento.

Sin historial, la fecha estimada es el vencimiento. Los documentos ya vencidos
se tratan como presión inmediata desde la fecha base.

## 5. Comportamiento de pago

Se calculan cantidad de documentos, media y mediana de atraso, monto aplicado,
última fecha y clasificación. La mediana se calcula en Python porque la base usa
un modo de compatibilidad SQL que no admite `PERCENTILE_CONT`.

Confianza del comportamiento:

- alta: 10 o más documentos;
- media: 3 a 9;
- baja: 1 o 2.

## 6. Estimación de fechas

Los atrasos históricos se acotan para evitar fechas absurdas:

- clientes: -30 a 90 días;
- proveedores: -15 a 60 días.

Ninguna fecha proyectada se coloca antes de la fecha base.

## 7. Escenarios

- Base: mediana histórica; defaults de 7 días para cobros y 0 para pagos.
- Optimista: cobros siete días antes; pagos al vencimiento normal.
- Pesimista: cobros quince días después; pagos mantienen presión contractual o
  histórica, y vencidos se reconocen inmediatamente.

Horizontes admitidos: 4, 8, 13 y 26 semanas.

## 8. Caja inicial

Sin parámetro manual, se buscan cuentas contabilizables de clase 10 con nombres
de caja, banco, efectivo o depósito. Al 2025-12-23 se detectaron 38 cuentas y una
caja inicial estimada de 206,706.78.

El usuario puede reemplazarla con `opening_cash`. Si no hay detección confiable,
el motor usa cero y devuelve una advertencia.

## 9. Alertas

Se generan alertas por:

- déficit;
- mayor salida neta;
- concentración en clientes o proveedores;
- CxC/CxP vencida relevante;
- caja inicial no identificada;
- moneda de reporte pendiente;
- déficit en escenario pesimista.

## 10. Explicaciones

Las explicaciones son reglas determinísticas sobre fuente documental, escenario,
semana crítica, concentración y origen de caja inicial.

## 11. Recomendaciones

Incluyen priorización de cobranza, revisión de pagos fuertes, negociación de
obligaciones, seguimiento a clientes concentradores y definición de moneda.

## 12. Confianza

El 93.6% del monto abierto tiene historial identificado. La caja inicial también
fue detectada. Sin embargo, la confianza global se mantiene **baja** porque aún
no existe una moneda oficial de reporte y los documentos combinan valores
locales de SAP.

## 13. Resultados

Con caja inicial detectada:

| Escenario | Cobros | Pagos | Caja final | Caja mínima | Semanas déficit |
|---|---:|---:|---:|---:|---:|
| Optimista | 1,796,209.99 | 2,283,484.72 | -280,567.95 | -417,000.52 | 13 |
| Base | 1,777,293.49 | 2,283,484.72 | -299,484.45 | -343,956.67 | 13 |
| Pesimista | 1,750,248.81 | 2,283,484.72 | -326,529.13 | -719,754.56 | 13 |

Dentro de 13 semanas se proyectan 225 CxC y 261 CxP en escenario base. Los demás
documentos tienen fechas estimadas fuera del horizonte.

Con `opening_cash=1,000,000`, el escenario base termina en 493,808.77, con caja
mínima de 449,336.55 y cero semanas en déficit.

## 14. Limitaciones

- Moneda oficial pendiente.
- Fechas estimadas no garantizan pagos reales.
- Solo se consideran documentos abiertos ya registrados.
- No se incluyen líneas de crédito, préstamos o pagos futuros no registrados.
- La estimación depende de conciliación correcta en SAP.
- La caja detectada debe validarse con Tesorería.
- Vista gerencial, no estado financiero oficial.

## 15. Endpoints

- `GET /api/cashflow-projection/payment-behavior`
- `GET /api/cashflow-projection/projectable-documents`
- `GET /api/cashflow-projection/weekly`
- `GET /api/cashflow-projection/scenarios`
- `GET /api/cashflow-projection/executive-summary`

Los cinco endpoints y los endpoints representativos de Fases 1–3 respondieron
HTTP 200. La suite completa terminó con `24 passed`.

## 16. Decisiones técnicas

- Consultas parametrizadas y de solo lectura.
- Medianas calculadas en Python por compatibilidad SQL.
- Reglas conservadoras y trazables.
- Ningún escenario se persiste.
- Errores y datos faltantes se devuelven como warnings.

## 17. Recomendación para Fase 5

Validar caja y moneda con Tesorería. Después, construir CxC predictiva detallada
por factura y cliente, reutilizando comportamiento histórico, concentración,
aging y fecha estimada desarrollados en esta fase.
