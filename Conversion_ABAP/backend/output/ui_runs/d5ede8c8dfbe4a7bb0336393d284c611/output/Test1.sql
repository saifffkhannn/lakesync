CREATE OR REPLACE VIEW zdemo_abap_cds_ve_joins AS
SELECT 
  _carr.carrid,
  _carr.carrname,
  _flsch_in.cityfrom AS cityfr_in,
  _flsch_in.cityto AS cityto_in
FROM zdemo_abap_carr AS _carr
INNER JOIN zdemo_abap_flsch AS _flsch_in ON _carr.carrid = _flsch_in.carrid;
