CREATE OR REPLACE VIEW zdemo_abap_cds_ve_sel(
  p_smax
) AS
SELECT
  -- Key fields
  carrid AS CarrierId,
  connid AS Connid,
  fldate,
  price,
  currency,
  paymentsum,
  planetype,
  seatsmax,
  seatsocc,
  
  -- Literals
  12345 AS int4,
  'hallo' AS c5,
  DATE '2024-01-01' AS date_lit,
  12.34 AS curr,
  0.9 AS discnt,
  'KM' AS kilometers,
  'Minutes' AS fltime_ut,
  1 AS num_lit,
  
  -- Parameters
  p_smax AS param,
  
  -- Session variables
  CURRENT_USER() AS usr,
  'CLIENT_PLACEHOLDER' AS clnt,
  'EN' AS langu,
  CURRENT_DATE() AS sys_date,
  CURRENT_TIMEZONE() AS usr_time,
  CURRENT_DATE() AS usr_date,
  
  -- Cast expressions
  CAST(price AS DECIMAL(15,2)) AS cast_curr2dec,
  CAST(DATE '2024-01-01' AS VARCHAR(8)) AS cast_dats2c,
  
  -- Arithmetic expressions
  seatsocc_b + seatsocc_f AS occ_seats_classes,
  seatsmax - seatsocc AS free_seats,
  2 * 2 AS mult,
  9 / 3 AS div,
  CAST(paymentsum AS DECIMAL(17,2)) * 0.75 AS discount_1,
  CAST(price AS DECIMAL(15,2)) * 0.9 AS discount_2,
  CAST(seatsocc / seatsmax * 100 AS DECIMAL(10,2)) AS occupancy_rate,
  
  -- Case expressions
  CASE currency
    WHEN 'EUR' THEN 'X'
    WHEN 'USD' THEN 'Y'
    ELSE 'Z'
  END AS case1,
  
  CASE 
    WHEN currency = 'EUR' THEN 'A'
    ELSE NULL
  END AS case2,
  
  CASE
    WHEN seatsmax <= 150 THEN 'small'
    WHEN seatsmax > 150 AND seatsmax < 300 THEN 'middle'
    WHEN seatsmax >= 300 THEN 'large'
    ELSE '?'
  END AS case3,
  
  -- Complex case with logical expressions
  CASE
    WHEN seatsmax = 385 AND NOT (seatsocc > 380 AND seatsocc <> 379 OR seatsocc <= 120 OR paymentsum >= 200000) THEN 'A'
    WHEN seatsmax BETWEEN 250 AND 350 AND seatsocc NOT BETWEEN 1 AND 100 THEN 'B'
    WHEN carrid LIKE '_L' THEN 'C'
    WHEN currency IS NOT NULL OR carrid IS NOT NULL THEN 'D'
    ELSE '?'
  END AS case4,
  
  -- Numeric functions
  ABS(-1) AS nf_abs,
  CEIL(3.333) AS nf_ceil,
  FLOOR(3.333) AS nf_floor,
  DIV0(25, 5) AS nf_div,
  MOD(11, 3) AS nf_mod,
  ROUND(1 / 3, 2) AS nf_division,
  ROUND(1.337, 2) AS nf_round,
  
  -- String functions
  CONCAT(planetype, '-#') AS sf_concat,
  CONCAT(CONCAT(carrid, REPEAT(' ', 1)), '#') AS sf_conc_ws,
  POSITION('U' IN currency) AS sf_instr,
  LEFT(currency, 2) AS sf_left,
  LENGTH(RTRIM(planetype)) AS sf_len,
  LOWER(carrid) AS sf_lower,
  LPAD(carrid, 5, '#') AS sf_lpad,
  LTRIM(planetype, 'A') AS sf_ltrim,
  REPLACE(currency, 'U', '#') AS sf_repl,
  REGEXP_REPLACE(planetype, '\\d', '#') AS sf_repl_regex,
  RIGHT(currency, 2) AS sf_right,
  RPAD(carrid, 5, '#') AS sf_rpad,
  RTRIM(planetype, '0') AS sf_rtrim,
  SUBSTR(planetype, 4, 3) AS sf_sub,
  UPPER('abap') AS sf_upper,
  
  -- Coalesce function
  COALESCE(carrid, 'N') AS coalesced,
  
  -- Type conversion (approximated)
  CAST(12.34 AS DECIMAL(10,1)) AS fltp2dec,
  
  -- Unit conversion (approximated as miles to km)
  p_smax * 1.60934 AS converted_value,
  
  -- Date functions
  DATEDIFF('day', fldate, DATE '2024-01-01') AS days_bw1,
  DATEDIFF('day', fldate, CURRENT_DATE()) AS days_bw2,
  DATEADD('day', 7, CURRENT_DATE()) AS in1week,
  
  -- Timestamp functions
  CURRENT_TIMESTAMP() AS ts,
  DATEADD('second', 60, CURRENT_TIMESTAMP()) AS in1minute
  
FROM zdemo_abap_fli
WHERE seatsmax > p_smax
