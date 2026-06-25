ACCOUNT_MOVEMENTS_SQL = """
SELECT
    O.RefDate AS posting_date,
    A.AcctCode AS account_code,
    A.FormatCode AS format_code,
    A.AcctName AS account_name,
    A.GroupMask AS group_mask,
    A.ActType AS act_type,
    COALESCE(J.Debit, 0) AS debit,
    COALESCE(J.Credit, 0) AS credit,
    CAST(NULL AS nvarchar(8)) AS OcrCode,
    J.OcrCode2,
    J.OcrCode3,
    J.OcrCode4,
    J.OcrCode5
FROM OJDT O
JOIN JDT1 J ON J.TransId = O.TransId
JOIN OACT A ON A.AcctCode = J.Account
WHERE O.RefDate >= :date_from
  AND O.RefDate < DATEADD(day, 1, :date_to)
"""

MONTHLY_ACCOUNT_MOVEMENTS_SQL = """
SELECT
    DATEFROMPARTS(YEAR(O.RefDate), MONTH(O.RefDate), 1) AS month_start,
    MAX(O.RefDate) AS month_max_date,
    A.AcctCode AS account_code,
    A.FormatCode AS format_code,
    A.AcctName AS account_name,
    A.GroupMask AS group_mask,
    A.ActType AS act_type,
    SUM(COALESCE(J.Debit, 0)) AS debit,
    SUM(COALESCE(J.Credit, 0)) AS credit
FROM OJDT O
JOIN JDT1 J ON J.TransId = O.TransId
JOIN OACT A ON A.AcctCode = J.Account
WHERE O.RefDate >= :date_from
  AND O.RefDate < DATEADD(day, 1, :date_to)
  AND O.TransType <> '-3'
GROUP BY
    DATEFROMPARTS(YEAR(O.RefDate), MONTH(O.RefDate), 1),
    A.AcctCode, A.FormatCode, A.AcctName, A.GroupMask, A.ActType
ORDER BY month_start
"""

BALANCE_MOVEMENTS_SQL = """
SELECT
    A.AcctCode AS account_code,
    A.FormatCode AS format_code,
    A.AcctName AS account_name,
    A.GroupMask AS group_mask,
    A.ActType AS act_type,
    SUM(COALESCE(J.Debit, 0)) AS debit,
    SUM(COALESCE(J.Credit, 0)) AS credit
FROM OJDT O
JOIN JDT1 J ON J.TransId = O.TransId
JOIN OACT A ON A.AcctCode = J.Account
WHERE O.RefDate <= :as_of_date
GROUP BY A.AcctCode, A.FormatCode, A.AcctName, A.GroupMask, A.ActType
"""

ACCOUNTS_SQL = """
SELECT AcctCode AS account_code, FormatCode AS format_code,
       AcctName AS account_name, GroupMask AS group_mask,
       ActType AS act_type, Levels AS levels, FatherNum AS father_num,
       Postable AS postable
FROM OACT
"""

AVAILABLE_PERIOD_SQL = """
SELECT MIN(RefDate) AS min_date, MAX(RefDate) AS max_date,
       COUNT(DISTINCT DATEFROMPARTS(YEAR(RefDate), MONTH(RefDate), 1)) AS months_count
FROM OJDT
"""

CURRENCIES_SQL = """
SELECT DISTINCT currency
FROM (
    SELECT DocCur AS currency FROM OINV WHERE CANCELED = 'N'
    UNION
    SELECT DocCur AS currency FROM OPCH WHERE CANCELED = 'N'
) C
WHERE NULLIF(LTRIM(RTRIM(currency)), '') IS NOT NULL
ORDER BY currency
"""

COST_CENTERS_SQL = """
SELECT PrcCode AS code, PrcName AS name, DimCode AS dimension,
       Active AS active
FROM OPRC
ORDER BY DimCode, PrcCode
"""

DIMENSION_COLUMNS_SQL = """
SELECT COLUMN_NAME
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'JDT1'
  AND COLUMN_NAME IN ('OcrCode', 'OcrCode2', 'OcrCode3', 'OcrCode4', 'OcrCode5')
"""

HISTORICAL_COLLECTIONS_SQL = """
SELECT DocDate AS movement_date, SUM(CAST(DocTotal AS decimal(28, 6))) AS amount
FROM ORCT
WHERE Canceled = 'N' AND DocDate >= :date_from
  AND DocDate < DATEADD(day, 1, :date_to)
GROUP BY DocDate
"""

HISTORICAL_PAYMENTS_SQL = """
SELECT DocDate AS movement_date, SUM(CAST(DocTotal AS decimal(28, 6))) AS amount
FROM OVPM
WHERE Canceled = 'N' AND DocDate >= :date_from
  AND DocDate < DATEADD(day, 1, :date_to)
GROUP BY DocDate
"""
