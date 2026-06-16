@EndUserText.label : 'Sales Order Header'
@AbapCatalog.enhancement.category : #EXTENSIBLE_ANY
@AbapCatalog.tableCategory : #TRANSPARENT
@AbapCatalog.deliveryClass : #A
@AbapCatalog.dataMaintenance : #ALLOWED
define table zsales_order_hdr {

  key mandt       : mandt not null;
  key vbeln       : vbeln_va not null;

  erdat           : erdat;
  erzet           : erzet;
  ernam           : ernam;
  angdt           : angdt;
  bnddt           : bnddt;
  audat           : audat;
  vbtyp           : vbtyp;
  trvog           : trvog;
  auart           : auart;
  augru           : augru;
  gwldt           : gwldt;
  bstnk           : bstnk;
  bstdk           : bstdk;
  bsark           : bsark;
  ihrez           : ihrez;
  bname           : bname;
  bstlf           : bstlf;
  vsart           : vsart;
  vsbed           : vsbed;
  shzue           : shzue;
  kunnr           : kunnr;
  stafo           : stafo;
  stwae           : stwae;
  aedat           : aedat;
  kvgr1           : kvgr1;
  kvgr2           : kvgr2;
  kvgr3           : kvgr3;
  kvgr4           : kvgr4;
  kvgr5           : kvgr5;
  vkorg           : vkorg;
  vtweg           : vtweg;
  spart           : spart;
  vkgrp           : vkgrp;
  vkbur           : vkbur;
  knumv           : knumv;
  waerk           : waerk;
  kurst           : kurst;
  kurrf           : kurrf;
  netwr           : netwr_ak;
  mwsbk           : mwsbk_ak;
  knumv_k         : knumv;
  vdatu           : edatu;
  zterm           : dzterm;
  inco1           : inco1;
  inco2           : inco2;
  lifsk           : lifsk;
  faksk           : faksk;
  autlf           : autlf;
  kzazu           : kzazu;
  guebg           : guebg;
  gueen           : gueen;
  objnr           : j_objnr;

}
