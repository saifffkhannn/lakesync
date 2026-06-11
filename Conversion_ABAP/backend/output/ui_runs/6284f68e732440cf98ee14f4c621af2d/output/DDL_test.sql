CREATE OR REPLACE VIEW Z_I_SalesAnalytics AS
SELECT
    Header.vbeln AS SalesOrder,
    Item.posnr AS ItemNumber,
    Header.auart AS OrderType,
    Item.netwr AS NetValue,
    CASE
        WHEN Item.netwr > 100000
             THEN 'HIGH'
        ELSE 'NORMAL'
    END AS SalesCategory
FROM vbak AS Header
INNER JOIN vbap AS Item
    ON Header.vbeln = Item.vbeln
