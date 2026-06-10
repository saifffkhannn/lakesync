-- ABAP CDS view entity: Joins converted to Snowflake
-- Original: zdemo_abap_cds_ve_joins
-- This view demonstrates the inner join pattern that was active in the ABAP source

CREATE OR REPLACE VIEW zdemo_abap_cds_ve_joins AS
SELECT 
    _carr.carrid,
    _carr.carrname,
    _flsch_in.cityfrom AS cityfr_in,
    _flsch_in.cityto AS cityto_in
FROM zdemo_abap_carr AS _carr
INNER JOIN zdemo_abap_flsch AS _flsch_in 
    ON _carr.carrid = _flsch_in.carrid;

-- Alternative view patterns for the commented-out join types:
-- Uncomment and use as needed based on business requirements

/*
-- LEFT OUTER JOIN version:
CREATE OR REPLACE VIEW zdemo_abap_cds_ve_joins_left AS
SELECT 
    _carr.carrid,
    _carr.carrname,
    _flsch_lo.cityfrom AS cityfr_lo,
    COALESCE(_flsch_lo.cityto, '???') AS cityto_lo
FROM zdemo_abap_carr AS _carr
LEFT OUTER JOIN zdemo_abap_flsch AS _flsch_lo 
    ON _carr.carrid = _flsch_lo.carrid;

-- RIGHT OUTER JOIN version:
CREATE OR REPLACE VIEW zdemo_abap_cds_ve_joins_right AS
SELECT 
    CASE WHEN _carr.url IS NOT NULL THEN _carr.url
         ELSE '!!!'
    END AS url_ro,
    _flsch_ro.cityfrom AS cityfr_ro,
    _flsch_ro.cityto AS cityto_ro
FROM zdemo_abap_carr AS _carr
RIGHT OUTER JOIN zdemo_abap_flsch AS _flsch_ro 
    ON _carr.carrid = _flsch_ro.carrid;

-- CROSS JOIN version:
CREATE OR REPLACE VIEW zdemo_abap_cds_ve_joins_cross AS
SELECT 
    _carr.carrid,
    _carr.carrname,
    _flsch_cr.cityfrom AS cityfr_cr,
    _flsch_cr.cityto AS cityto_cr
FROM zdemo_abap_carr AS _carr
CROSS JOIN zdemo_abap_flsch AS _flsch_cr;
*/
