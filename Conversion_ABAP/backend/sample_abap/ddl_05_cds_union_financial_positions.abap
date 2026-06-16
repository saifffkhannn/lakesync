@AbapCatalog.sqlViewName: 'ZVFINANCIALPOS'
@AbapCatalog.compiler.compareFilter: true
@AbapCatalog.preserveKey: true
@AccessControl.authorizationCheck: #NOT_REQUIRED
@EndUserText.label: 'Unified Financial Positions - AR/AP Open Items'
@VDM.viewType: #COMPOSITE
@Analytics.dataCategory: #FACT

define view ZI_FinancialPositions
  with parameters
    p_keydate  : dats,
    p_bukrs    : bukrs,
    p_currency : waers

  as select from bsid as ar   -- AR Open Items

{
  key ar.mandt                                as Client,
  key ar.bukrs                                as CompanyCode,
  key ar.belnr                                as AccountingDocument,
  key ar.gjahr                                as FiscalYear,
  key ar.buzei                                as DocumentItem,

  'AR'                                        as AccountType,
  ar.kunnr                                    as BusinessPartner,
  ''                                          as VendorPartner,
  ar.bldat                                    as DocumentDate,
  ar.budat                                    as PostingDate,
  ar.faedt                                    as DueDate,

  @Semantics.currencyCode: true
  ar.waers                                    as DocumentCurrency,

  @Semantics.amount.currencyCode: 'DocumentCurrency'
  ar.dmbtr                                    as AmountLC,

  @Semantics.amount.currencyCode: 'DocumentCurrency'
  ar.wrbtr                                    as AmountDC,

  ar.shkzg                                    as DrCrIndicator,

  case ar.shkzg
    when 'S' then  ar.dmbtr
    when 'H' then  ar.dmbtr * ( -1 )
    else           cast( 0 as dmbtr )
  end                                         as SignedAmount,

  case
    when $parameters.p_keydate > ar.faedt
      then $parameters.p_keydate - ar.faedt
    else 0
  end                                         as DaysOverdue,

  case
    when $parameters.p_keydate > ar.faedt
      and $parameters.p_keydate - ar.faedt between 1 and 30
      then '01-30'
    when $parameters.p_keydate > ar.faedt
      and $parameters.p_keydate - ar.faedt between 31 and 60
      then '31-60'
    when $parameters.p_keydate > ar.faedt
      and $parameters.p_keydate - ar.faedt between 61 and 90
      then '61-90'
    when $parameters.p_keydate > ar.faedt
      and $parameters.p_keydate - ar.faedt > 90
      then '90+'
    else 'Current'
  end                                         as AgingBucket,

  ar.zterm                                    as PaymentTerms,
  ar.mahns                                    as DunningLevel,
  ar.sgtxt                                    as ItemText,
  ar.zuonr                                    as Assignment,
  ar.augdt                                    as ClearingDate,
  ar.augbl                                    as ClearingDocument,
  ar.blart                                    as DocumentType,
  ar.mwskz                                    as TaxCode,
  ar.hkont                                    as GLAccount

}
where ar.bukrs = $parameters.p_bukrs
  and ar.augdt = '00000000'   -- Open items only

union all

select from bsik as ap   -- AP Open Items

{
  key ap.mandt,
  key ap.bukrs,
  key ap.belnr,
  key ap.gjahr,
  key ap.buzei,

  'AP'                                        as AccountType,
  ''                                          as BusinessPartner,
  ap.lifnr                                    as VendorPartner,
  ap.bldat,
  ap.budat,
  ap.faedt,

  @Semantics.currencyCode: true
  ap.waers,

  @Semantics.amount.currencyCode: 'DocumentCurrency'
  ap.dmbtr,

  @Semantics.amount.currencyCode: 'DocumentCurrency'
  ap.wrbtr,

  ap.shkzg,

  case ap.shkzg
    when 'H' then  ap.dmbtr
    when 'S' then  ap.dmbtr * ( -1 )
    else           cast( 0 as dmbtr )
  end,

  case
    when $parameters.p_keydate > ap.faedt
      then $parameters.p_keydate - ap.faedt
    else 0
  end,

  case
    when $parameters.p_keydate > ap.faedt
      and $parameters.p_keydate - ap.faedt between 1 and 30
      then '01-30'
    when $parameters.p_keydate > ap.faedt
      and $parameters.p_keydate - ap.faedt between 31 and 60
      then '31-60'
    when $parameters.p_keydate > ap.faedt
      and $parameters.p_keydate - ap.faedt between 61 and 90
      then '61-90'
    when $parameters.p_keydate > ap.faedt
      and $parameters.p_keydate - ap.faedt > 90
      then '90+'
    else 'Current'
  end,

  ap.zterm,
  ap.mahns,
  ap.sgtxt,
  ap.zuonr,
  ap.augdt,
  ap.augbl,
  ap.blart,
  ap.mwskz,
  ap.hkont

}
where ap.bukrs = $parameters.p_bukrs
  and ap.augdt = '00000000'
