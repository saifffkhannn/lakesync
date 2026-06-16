@AbapCatalog.sqlViewName: 'ZVSALESANALYSIS'
@AbapCatalog.compiler.compareFilter: true
@AbapCatalog.preserveKey: true
@AccessControl.authorizationCheck: #CHECK
@EndUserText.label: 'Sales Analysis CDS View'
@Analytics.dataCategory: #CUBE
@Analytics.settings.maxProcessingEffort: #HIGH

@VDM.viewType: #COMPOSITE
@OData.publish: true

define view ZC_SalesAnalysis
  as select from zsales_order_hdr as hdr
  inner join   zsales_order_itm  as itm  on  itm.mandt = hdr.mandt
                                          and itm.vbeln = hdr.vbeln
  inner join   zcustomer_master  as cust on  cust.mandt = hdr.mandt
                                          and cust.kunnr = hdr.kunnr
  left outer join zmaterial_master as mat on  mat.mandt = hdr.mandt
                                          and mat.matnr = itm.matnr

{
  @Analytics.dimension.zeroValueHandling : #SET_NULL
  key hdr.vbeln                               as SalesDocument,
  key itm.posnr                               as SalesDocumentItem,

  @Semantics.businessDate.at: true
  hdr.audat                                   as OrderDate,

  @Semantics.businessDate.from: true
  hdr.vdatu                                   as RequestedDeliveryDate,

  @Semantics.organization.companyCode: true
  hdr.vkorg                                   as SalesOrg,

  hdr.vtweg                                   as DistributionChannel,
  hdr.spart                                   as Division,
  hdr.vkgrp                                   as SalesGroup,
  hdr.vkbur                                   as SalesOffice,
  hdr.auart                                   as OrderType,

  @Semantics.currencyCode: true
  hdr.waerk                                   as TransactionCurrency,

  @Semantics.amount.currencyCode: 'TransactionCurrency'
  hdr.netwr                                   as NetValue,

  @Semantics.amount.currencyCode: 'TransactionCurrency'
  hdr.mwsbk                                   as TaxAmount,

  @Semantics.amount.currencyCode: 'TransactionCurrency'
  itm.netwr                                   as ItemNetValue,

  @Semantics.amount.currencyCode: 'TransactionCurrency'
  itm.kwmeng                                  as OrderQuantity,

  @Semantics.unitOfMeasure: true
  itm.vrkme                                   as SalesUnit,

  hdr.kunnr                                   as SoldToParty,
  cust.name1                                  as CustomerName,
  cust.land1                                  as Country,
  cust.regio                                  as Region,
  cust.ktokd                                  as CustomerGroup,
  cust.brsch                                  as Industry,

  itm.matnr                                   as Material,
  mat.matkl                                   as MaterialGroup,
  mat.mtart                                   as MaterialType,
  mat.meins                                   as BaseUOM,

  itm.werks                                   as Plant,
  itm.lgort                                   as StorageLocation,

  hdr.lifsk                                   as DeliveryBlock,
  hdr.faksk                                   as BillingBlock,

  @Semantics.user.createdBy: true
  hdr.ernam                                   as CreatedBy,

  @Semantics.systemDate.createdAt: true
  hdr.erdat                                   as CreatedOn,

  // Calculated fields
  case hdr.lifsk
    when '' then 'Not Blocked'
    else        'Blocked'
  end                                         as DeliveryStatus,

  concat( concat( hdr.vkorg, '/' ), hdr.vtweg ) as SalesArea,

  @DefaultAggregation: #SUM
  @Semantics.amount.currencyCode: 'TransactionCurrency'
  itm.netwr - itm.kzwi1                      as ContributionMargin

}
where hdr.vbtyp = 'C'   -- Standard Orders only
