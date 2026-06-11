@EndUserText.label : 'Financial Document Line Items'
@AbapCatalog.enhancement.category : #NOT_EXTENSIBLE
@AbapCatalog.tableCategory : #TRANSPARENT
@AbapCatalog.deliveryClass : #A
@AbapCatalog.dataMaintenance : #LIMITED
define table zfi_doc_line_items {

  key mandt       : mandt not null;
  key bukrs       : bukrs not null;        -- Company Code
  key belnr       : belnr_d not null;      -- Accounting Document Number
  key gjahr       : gjahr not null;        -- Fiscal Year
  key buzei       : buzei not null;        -- Posting Line

  blart           : blart;                 -- Document Type
  bldat           : bldat;                 -- Document Date
  budat           : budat;                 -- Posting Date
  monat           : monat;                 -- Fiscal Period
  cpudt           : cpudt;                 -- Entry Date
  cputm           : cputm;                 -- Entry Time
  usnam           : usnam;                 -- User Name
  tcode           : tcode;                 -- Transaction Code
  bvorg           : bvorg;                 -- Business Transaction
  xblnr           : xblnr1;               -- External Reference
  awtyp           : awtyp;                 -- Reference Transaction
  awref           : awref;                 -- Reference Document
  aworg           : aworg;                 -- Reference Org Unit
  awsys           : logsys;               -- Logical System

  -- GL Account
  hkont           : hkont;
  saknr           : saknr;
  shkzg           : shkzg;                 -- Debit/Credit Indicator

  -- Amount Fields
  dmbtr           : dmbtr;                 -- Amount in Local Currency
  wrbtr           : wrbtr;                 -- Amount in Document Currency
  txbhw           : txbhw;                 -- Tax Base Amount LC
  mwsts           : mwsts;                 -- Tax Amount LC
  hwbas           : hwbas;                 -- Tax Base HC

  -- Currency
  waers           : waers;                 -- Document Currency
  hwaer           : hwaer;                 -- Local Currency
  kwaer           : kwaer;                 -- Group Currency
  zwbtr           : zwbtr;                 -- Amount in 2nd Local Currency
  hwbtr           : hwbtr;                 -- Amount in 3rd Local Currency

  -- Exchange Rate
  kursf           : kursf;                 -- Exchange Rate
  pswbt           : pswbt;                 -- Amount for Ledger (PCA)
  pswsl           : pswsl;                 -- Currency for Ledger

  -- Partner Objects
  kostl           : kostl;                 -- Cost Center
  aufnr           : aufnr;                 -- Order Number
  ps_psp_pnr      : ps_psp_pnr;           -- WBS Element
  prctr           : prctr;                 -- Profit Center
  segment         : fb_segment;            -- Segment
  gsber           : gsber;                 -- Business Area
  kokrs           : kokrs;                 -- Controlling Area

  -- Tax
  mwskz           : mwskz;                 -- Tax Code
  qsskz           : qsskz;                 -- Withholding Tax Code
  qsshb           : qsshb;                 -- WHT Subject Amount
  qsfbt           : qsfbt;                 -- WHT Exempt Amount

  -- Vendor/Customer
  lifnr           : lifnr;                 -- Vendor
  kunnr           : kunnr;                 -- Customer
  umsks           : umsks;                 -- Special GL Indicator
  umskz           : umskz;                 -- Special GL Indicator (tgt)
  zuonr           : dzuonr;               -- Assignment

  -- Payment
  zterm           : dzterm;               -- Payment Terms
  zbd1t           : dzbd1t;               -- Cash Discount Days 1
  zbd2t           : dzbd2t;               -- Cash Discount Days 2
  zbd3t           : dzbd3t;               -- Net Due Days
  zbd1p           : dzbd1p;               -- Cash Discount % 1
  zbd2p           : dzbd2p;               -- Cash Discount % 2
  skfbt           : skfbt;               -- Amount Eligible for Cash Disc.
  sknto           : sknto;               -- Cash Discount Amount
  wskto           : wskto;               -- Cash Discount in Doc Currency
  mschl           : mschl;               -- Dunning Key
  mahns           : mahns;               -- Dunning Level
  mansp           : mansp;               -- Dunning Block

  -- Clearing
  augdt           : augdt;               -- Clearing Date
  augbl           : augbl;               -- Clearing Document
  auggj           : auggj;               -- Clearing Fiscal Year

  -- Text
  sgtxt           : sgtxt;               -- Item Text
  xref1           : xref1_hd;           -- Reference Key 1
  xref2           : xref2_hd;           -- Reference Key 2
  xref3           : xref3;              -- Reference Key 3

  -- Logistics
  matnr           : matnr;              -- Material
  werks           : werks_d;            -- Plant
  menge           : menge_d;            -- Quantity
  meins           : meins;              -- UOM
  ebeln           : ebeln;              -- PO Number
  ebelp           : ebelp;              -- PO Item
  zekkn           : zekkn;              -- PO Account Assignment

}
