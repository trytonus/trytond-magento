# -*- coding: utf-8 -*-
from trytond.pool import Pool
from wizard import (
    TestMagentoConnectionStart, ImportWebsitesStart,
    ExportMagentoShipmentStatusStart,
    ExportMagentoShipmentStatus, ConfigureMagento, ImportStoresStart,
    FailureStart, UpdateMagentoCatalogStart, UpdateMagentoCatalog,
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
from carrier import SaleChannelCarrier
from sale import (
    Sale, StockShipmentOut, SaleLine
)
from bom import BOM
from payment import MagentoPaymentGateway, Payment


def register():
    """
    Register classes
    """
    Pool.register(
        Channel,
        MagentoTier,
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
        SaleChannelCarrier,
        SaleLine,
        BOM,
        ProductSaleChannelListing,
        MagentoPaymentGateway,
        Payment,
        module='magento', type_='model'
    )
    Pool.register(
        ExportMagentoShipmentStatus,
        ExportDataWizard,
        ConfigureMagento,
        UpdateMagentoCatalog,
        module='magento', type_='wizard'
    )
