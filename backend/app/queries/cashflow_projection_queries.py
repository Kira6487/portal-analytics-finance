CUSTOMER_PAYMENT_BEHAVIOR_SQL = """
WITH paid_documents AS (
    SELECT
        I.DocEntry,
        I.CardCode,
        I.CardName,
        I.DocDueDate,
        MAX(P.DocDate) AS payment_date,
        SUM(COALESCE(R.SumApplied, 0)) AS applied_amount
    FROM OINV I
    JOIN RCT2 R ON R.DocEntry = I.DocEntry AND R.InvType = '13'
    JOIN ORCT P ON P.DocEntry = R.DocNum AND P.Canceled = 'N'
    WHERE I.CANCELED = 'N'
    GROUP BY I.DocEntry, I.CardCode, I.CardName, I.DocDueDate
)
SELECT
    CardCode AS card_code,
    CardName AS card_name,
    DATEDIFF(day, DocDueDate, payment_date) AS delay_days,
    CAST(applied_amount AS decimal(28, 6)) AS paid_amount,
    payment_date
FROM paid_documents
"""

VENDOR_PAYMENT_BEHAVIOR_SQL = """
WITH paid_documents AS (
    SELECT
        I.DocEntry,
        I.CardCode,
        I.CardName,
        I.DocDueDate,
        MAX(P.DocDate) AS payment_date,
        SUM(COALESCE(R.SumApplied, 0)) AS applied_amount
    FROM OPCH I
    JOIN VPM2 R ON R.DocEntry = I.DocEntry AND R.InvType = '18'
    JOIN OVPM P ON P.DocEntry = R.DocNum AND P.Canceled = 'N'
    WHERE I.CANCELED = 'N'
    GROUP BY I.DocEntry, I.CardCode, I.CardName, I.DocDueDate
)
SELECT
    CardCode AS card_code,
    CardName AS card_name,
    DATEDIFF(day, DocDueDate, payment_date) AS delay_days,
    CAST(applied_amount AS decimal(28, 6)) AS paid_amount,
    payment_date
FROM paid_documents
"""

DATA_BASIS_DATE_SQL = """
SELECT MAX(max_date) AS basis_date
FROM (
    SELECT MAX(RefDate) AS max_date FROM OJDT
    UNION ALL SELECT MAX(DocDate) FROM OINV
    UNION ALL SELECT MAX(DocDate) FROM OPCH
) dates
"""

OPENING_CASH_SQL = """
SELECT
    COUNT(DISTINCT A.AcctCode) AS accounts_count,
    COALESCE(SUM(CAST(CASE WHEN O.TransId IS NOT NULL
        THEN COALESCE(J.Debit, 0) - COALESCE(J.Credit, 0) ELSE 0 END
        AS decimal(28, 6))), 0) AS opening_cash
FROM OACT A
LEFT JOIN JDT1 J ON J.Account = A.AcctCode
LEFT JOIN OJDT O ON O.TransId = J.TransId AND O.RefDate <= :basis_date
WHERE A.Postable = 'Y'
  AND A.GroupMask = 1
  AND A.FormatCode LIKE '10%'
  AND (
      UPPER(A.AcctName) LIKE '%CAJA%'
      OR UPPER(A.AcctName) LIKE '%BANCO%'
      OR UPPER(A.AcctName) LIKE '%EFECTIVO%'
      OR UPPER(A.AcctName) LIKE '%DEPOSITO%'
  )
"""
