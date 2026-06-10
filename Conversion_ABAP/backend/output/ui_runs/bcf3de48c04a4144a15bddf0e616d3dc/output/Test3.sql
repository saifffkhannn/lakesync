CREATE OR REPLACE VIEW zdemo_abap_cds_ve_sel AS
SELECT
  carrid AS CarrierId,
  zdemo_abap_fli.connid AS Connid,
  fldate,
  price,
  currency,
  paymentsum,
  planetype,
  seatsmax,
  seatsocc,
  12345 AS int4,
  'hallo' AS c5,
  '20240101' AS date_lit,
  12.34 AS curr,
  0.9 AS discnt,
  'KM' AS kilometers,
  'Minutes' AS fltime_ut,
  1 AS num_lit,
  :p_smax AS param,
  CURRENT_USER AS usr,
  'CLIENT' AS clnt,
  'LANGUAGE' AS langu,
  CURRENT_DATE AS sys_date,
  'TIMEZONE' AS usr_time,
  CURRENT_DATE AS usr_date,
  CAST(price AS DECIMAL(15,2)) AS cast_curr2dec,
  CAST(date_lit AS CHAR(8)) AS cast_dats2c,
  seatsocc_b + seatsocc_f AS occ_seats_classes,
  seatsmax - seatsocc AS free_seats,
  2 * 2 AS mult,
  9 / 3 AS div,
  CAST(paymentsum AS DECIMAL(17,2)) * 0.75 AS discount_1,
  cast_curr2dec * discnt AS discount_2,
  CAST(seatsocc / seatsmax * 100 AS DECIMAL(10,2)) AS occupancy_rate,
  CASE currency
    WHEN 'EUR' THEN 'X'
    WHEN 'USD' THEN 'Y'
    ELSE 'Z'
  END AS case1,
  CASE case1
    WHEN 'X' THEN 'A'
    ELSE NULL
  END AS case2,
  CASE
    WHEN seatsmax <= 150 THEN 'small'
    WHEN seatsmax > 150 AND seatsmax < 300 THEN 'middle'
    WHEN seatsmax >= 300 THEN 'large'
    ELSE '?'
  END AS case3,
  CASE
    WHEN seatsmax = 385 AND NOT (seatsocc > 380 AND seatsocc <> 379 OR seatsocc <= 120 OR paymentsum >= 200000) THEN 'A'
    WHEN seatsmax BETWEEN 250 AND 350 AND seatsocc NOT BETWEEN 1 AND 100 THEN 'B'
    WHEN carrid LIKE '_L' THEN 'C'
    WHEN currency IS NOT NULL OR carrid IS NOT NULL THEN 'D'
    ELSE '?'
  END AS case4,
  ABS(-1) AS nf_abs,
  CEIL(3.333) AS nf_ceil,
  FLOOR(3.333) AS nf_floor,
  DIV(25, 5) AS nf_div,
  MOD(11, 3) AS nf_mod,
  ROUND(1 / 3, 2) AS nf_division,
  ROUND(1.337, 2) AS nf_round,
  CONCAT(planetype, '-#') AS sf_concat,
  CONCAT(carrid, ' ', '#') AS sf_conc_ws,
  POSITION('U' IN currency) AS sf_instr,
  LEFT(currency, 2) AS sf_left,
  LENGTH(planetype) AS sf_len,
  LOWER(carrid) AS sf_lower,
  LPAD(carrid, 5, '#') AS sf_lpad,
  LTRIM(planetype, 'A') AS sf_ltrim,
  REPLACE(currency, 'U', '#') AS sf_repl,
  REGEXP_REPLACE(planetype, '\\d', '#') AS sf_repl_regex,
  RIGHT(currency, 2) AS sf_right,
  RPAD(carrid, 5, '#') AS sf_rpad,
  RTRIM(planetype, '0') AS sf_rtrim,
  SUBSTRING(planetype, 4, 3) AS sf_sub,
  UPPER('abap') AS sf_upper,
  COALESCE(carrid, 'N') AS coalesced,
  12.34 AS fltp2dec,
  :p_smax AS converted_value,
  DATEDIFF(DAY, fldate, date_lit) AS days_bw1,
  DATEDIFF(DAY, fldate, CURRENT_DATE) AS days_bw2,
  DATEADD(DAY, 7, CURRENT_DATE) AS in1week,
  CURRENT_TIMESTAMP AS ts,
  DATEADD(SECOND, 60, ts) AS in1minute
FROM zdemo_abap_fli
WHERE seatsmax > :p_smax
