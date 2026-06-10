CREATE OR REPLACE VIEW zdemo_abap_cds_ve_agg_exp AS
SELECT 
    carrid,
    currency,
    AVG(CAST(seatsocc AS DECIMAL(15,2))) AS avg_seats_occ,
    AVG(CAST(paymentsum AS DECIMAL(15,2))) AS avg_paysum,
    SUM(paymentsum) AS total_paysum,
    MIN(seatsocc) AS min_occ_seats,
    MAX(seatsocc) AS max_occ_seats,
    MAX(seatsocc) AS max_occ_seats_all,
    COUNT(*) AS cnt,
    COUNT(DISTINCT planetype) AS cnt_planetype
FROM zdemo_abap_fli
GROUP BY 
    carrid,
    currency
