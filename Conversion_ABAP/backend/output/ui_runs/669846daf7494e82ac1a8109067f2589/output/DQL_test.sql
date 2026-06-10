SELECT
    vbak.vbeln,
    vbak.auart,
    vbak.erdat,
    kna1.name1,
    vbap.matnr,
    vbap.kwmeng,
    vbap.netwr
FROM vbak
INNER JOIN vbap
    ON vbak.vbeln = vbap.vbeln
INNER JOIN kna1
    ON vbak.kunnr = kna1.kunnr
WHERE vbak.auart IN ('OR', 'TA')
  AND vbak.erdat >= '20240101';
