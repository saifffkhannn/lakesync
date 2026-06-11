@EndUserText.label : 'Customer Master Data'
@AbapCatalog.enhancement.category : #NOT_EXTENSIBLE
@AbapCatalog.tableCategory : #TRANSPARENT
@AbapCatalog.deliveryClass : #A
@AbapCatalog.dataMaintenance : #RESTRICTED
define table zcustomer_master {

  key mandt       : mandt not null;
  key kunnr       : kunnr not null;

  erdat           : erdat;
  ernam           : ernam;
  aedat           : aedat;
  name1           : name1_gp;
  name2           : name2_gp;
  sortl           : sortl;
  stras           : stras_gp;
  pfach           : pfach;
  pstlz           : pstlz;
  ort01           : ort01_gp;
  regio           : regio;
  land1           : land1_gp;
  telf1           : telf1;
  telfx           : telfx;
  smtp_addr       : ad_smtpadr;
  ktokd           : ktokd;
  spras           : spras;
  waers           : waers;
  kukla           : kukla;
  vbund           : vbund;
  lifnr           : lifnr;
  brsch           : brsch;
  stcd1           : stcd1;
  stcd2           : stcd2;
  stkzu           : stkzu;
  stkzn           : stkzn;
  crea_user       : syuname;
  crea_date       : sydatum;
  crea_time       : syuzeit;
  chng_user       : syuname;
  chng_date       : sydatum;

}
