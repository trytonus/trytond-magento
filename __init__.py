# -*- coding: utf-8 -*-
from trytond.pool import Pool
from wizard import (
    TestMagentoConnectionStart, ImportWebsitesStart,
    ExportMagentoShipmentStatusStart,
    ExportMagentoShipmentStatus, ImportMagentoCarriersStart,
    ImportMagentoCarriers, ConfigureMagento, ImportStoresStart, FailureStart,
    UpdateMagentoCatalogStart, UpdateMagentoCatalog,
    SuccessStart, ExportDataWizardConfigure, ExportDataWizard,
)
from channel import Channel, MagentoTier
from party import Party, MagentoWebsiteParty, Address
from product import (
    Category, MagentoInstanceCategory, Product,
    ProductPriceTier, ProductSaleChannelListing
)
from country import Country, Subdivision
from currency import Currency
from carrier import MagentoInstanceCarrier
from sale import (
    Sale, StockShipmentOut, SaleLine
)
from bom import BOM
from tax import MagentoTax, MagentoTaxRelation
from payment import MagentoPaymentGateway, Payment


def register():
    """
    Register classes
    """
    Pool.register(
        Channel,
        MagentoTier,
        MagentoInstanceCarrier,
        TestMagentoConnectionStart,
        ImportStoresStart,
        FailureStart,
        SuccessStart,
        ImportWebsitesStart,
        UpdateMagentoCatalogStart,
        ExportMagentoShipmentStatusStart,
        Country,
        Subdivision,
        Party,
        MagentoWebsiteParty,
        Category,
        MagentoInstanceCategory,
        Product,
        ProductPriceTier,
        ExportDataWizardConfigure,
        StockShipmentOut,
        Address,
        Currency,
        Sale,
        ImportMagentoCarriersStart,
        SaleLine,
        BOM,
        MagentoTax,
        MagentoTaxRelation,
        ProductSaleChannelListing,
        MagentoPaymentGateway,
        Payment,
        module='magento', type_='model'
    )
    Pool.register(
        ExportMagentoShipmentStatus,
        ExportDataWizard,
        ImportMagentoCarriers,
        ConfigureMagento,
        UpdateMagentoCatalog,
        module='magento', type_='wizard'
    )
