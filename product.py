# -*- coding: UTF-8 -*-
import magento
from collections import defaultdict

import logbook
from trytond.model import ModelSQL, ModelView, fields
from trytond.transaction import Transaction
from trytond.pool import PoolMeta, Pool
from trytond.pyson import Eval
from decimal import Decimal


__all__ = [
    'Category', 'MagentoInstanceCategory', 'Product',
    'ProductSaleChannelListing',
    'ProductPriceTier',
]
__metaclass__ = PoolMeta

log = logbook.Logger('magento', logbook.INFO)


def batch(iterable, n=1):
    l = len(iterable)
    for ndx in range(0, l, n):
        yield iterable[ndx:min(ndx + n, l)]


class Category:
    "Product Category"
    __name__ = "product.category"

    magento_ids = fields.One2Many(
        'magento.instance.product_category', 'category',
        'Magento IDs', readonly=True,
    )

    @classmethod
    def create_tree_using_magento_data(cls, category_tree):
        """
        Create the categories from the category tree

        :param category_tree: Category Tree from Magento
        """
        # Create the root
        root_category = cls.find_or_create_using_magento_data(
            category_tree
        )
        for child in category_tree['children']:
            cls.find_or_create_using_magento_data(
                child, parent=root_category
            )
            if child['children']:
                cls.create_tree_using_magento_data(child)

    @classmethod
    def find_or_create_using_magento_data(
        cls, category_data, parent=None
    ):
        """
        Find or Create category using Magento Database

        :param category_data: Category Data from Magento
        :param parent: Browse record of Parent if present, else None
        :returns: Active record of category found/created
        """
        category = cls.find_using_magento_data(
            category_data
        )

        if not category:
            category = cls.create_using_magento_data(
                category_data, parent
            )
        return category

    @classmethod
    def find_or_create_using_magento_id(
        cls, magento_id, parent=None
    ):
        """
        Find or Create Category Using Magento ID of Category

        :param category_data: Category Data from Magento
        :param parent: Browse record of Parent if present, else None
        :returns: Active record of category found/created
        """
        Channel = Pool().get('sale.channel')

        category = cls.find_using_magento_id(magento_id)
        if not category:
            channel = Channel.get_current_magento_channel()

            with magento.Category(
                channel.magento_url, channel.magento_api_user,
                channel.magento_api_key
            ) as category_api:
                category_data = category_api.info(magento_id)

            category = cls.create_using_magento_data(
                category_data, parent
            )

        return category

    @classmethod
    def find_using_magento_data(cls, category_data):
        """
        Find category using Magento Data

        :param category_data: Category Data from Magento
        :returns: Active record of category found or None
        """
        MagentoCategory = Pool().get('magento.instance.product_category')

        records = MagentoCategory.search([
            ('magento_id', '=', int(category_data['category_id'])),
            ('channel', '=', Transaction().context['current_channel'])
        ])
        return records and records[0].category or None

    @classmethod
    def find_using_magento_id(cls, magento_id):
        """
        Find category using Magento ID or Category

        :param magento_id: Category ID from Magento
        :type magento_id: Integer
        :returns: Active record of Category Found or None
        """
        MagentoCategory = Pool().get('magento.instance.product_category')

        records = MagentoCategory.search([
            ('magento_id', '=', magento_id),
            ('channel', '=', Transaction().context['current_channel'])
        ])

        return records and records[0].category or None

    @classmethod
    def create_using_magento_data(cls, category_data, parent=None):
        """
        Create category using magento data

        :param category_data: Category Data from magento
        :param parent: Browse record of Parent if present, else None
        :returns: Active record of category created
        """
        category, = cls.create([{
            'name': category_data['name'],
            'parent': parent,
            'magento_ids': [('create', [{
                'magento_id': int(category_data['category_id']),
                'channel': Transaction().context['current_channel'],
            }])],
        }])

        return category


class MagentoInstanceCategory(ModelSQL, ModelView):
    """
    Magento Instance - Product Category Store

    This model keeps a record of a category's association with an Instance
    and the ID of the category on that channel
    """
    __name__ = "magento.instance.product_category"

    magento_id = fields.Integer(
        'Magento ID', readonly=True, required=True, select=True
    )
    channel = fields.Many2One(
        'sale.channel', 'Magento Instance', readonly=True,
        required=True, select=True
    )
    category = fields.Many2One(
        'product.category', 'Product Category', readonly=True,
        required=True, select=True
    )

    @classmethod
    def __setup__(cls):
        '''
        Setup the class and define constraints
        '''
        super(MagentoInstanceCategory, cls).__setup__()
        cls._sql_constraints += [
            (
                'magento_id_instance_unique',
                'UNIQUE(magento_id, channel)',
                'Each category in an channel must be unique!'
            )
        ]


class ProductSaleChannelListing:
    "Product Sale Channel"
    __name__ = 'product.product.channel_listing'

    price_tiers = fields.One2Many(
        'product.price_tier', 'product_listing', 'Price Tiers'
    )
    magento_product_type = fields.Selection(
        [
            (None, ''),
            ('simple', 'Simple'),
            ('configurable', 'Configurable'),
            ('grouped', 'Grouped'),
            ('bundle', 'Bundle'),
            ('virtual', 'Virtual'),
            ('downloadable', 'Downloadable'),
        ], 'Magento Product Type', readonly=True, states={
            "invisible": Eval('channel_source') != 'magento'
        }, depends=['channel_source']
    )

    @classmethod
    def __setup__(cls):
        super(ProductSaleChannelListing, cls).__setup__()
        cls._error_messages.update({
            'multi_inventory_update_fail':
            "FaultCode: %s, FaultMessage: %s",
        })

    @classmethod
    def create_from(cls, channel, product_data):
        """
        Create a listing for the product from channel and data
        """
        Product = Pool().get('product.product')

        if channel.source != 'magento':
            return super(ProductSaleChannelListing, cls).create_from(
                channel, product_data
            )

        try:
            product, = Product.search([
                ('code', '=', product_data['sku']),
            ])
        except ValueError:
            cls.raise_user_error("No product found for mapping")

        listing = cls(
            channel=channel,
            product=product,
            # Do not match with SKU. Magento fucks up when there are
            # numeric SKUs
            product_identifier=product_data['product_id'],
            magento_product_type=product_data['type'],
        )
        listing.save()
        return listing

    def export_inventory(self):
        """
        Export inventory of this listing
        """
        if self.channel.source != 'magento':
            return super(ProductSaleChannelListing, self).export_inventory()

        return self.export_bulk_inventory([self])

    @classmethod
    def export_bulk_inventory(cls, listings):
        """
        Bulk export inventory to magento.

        Do not rely on the return value from this method.
        """
        SaleChannelListing = Pool().get('product.product.channel_listing')

        if not listings:
            # Nothing to update
            return

        non_magento_listings = cls.search([
            ('id', 'in', map(int, listings)),
            ('channel.source', '!=', 'magento'),
        ])
        if non_magento_listings:
            super(ProductSaleChannelListing, cls).export_bulk_inventory(
                non_magento_listings
            )
        magento_listings = filter(
            lambda l: l not in non_magento_listings, listings
        )

        log.info(
            "Fetching inventory of %d magento listings"
            % len(magento_listings)
        )

        inventory_channel_map = defaultdict(list)
        for listing in magento_listings:
            channel = listing.channel

            product_data = {
                'qty': listing.quantity,
            }

            # TODO: Get this from availability used
            if listing.magento_product_type == 'simple':
                # Only send inventory for simple products
                product_data['is_in_stock'] = '1' \
                    if listing.quantity > 0 else '0'
            else:
                # configurable, bundle and everything else
                product_data['is_in_stock'] = '1'

            # group inventory xml by channel
            inventory_channel_map[channel].append([
                listing.product_identifier, product_data
            ])

        for channel, product_data_list in inventory_channel_map.iteritems():
            with magento.Inventory(
                    channel.magento_url,
                    channel.magento_api_user,
                    channel.magento_api_key) as inventory_api:
                for product_data_batch in batch(product_data_list, 50):
                    log.info(
                        "Pushing inventory of %d products to magento"
                        % len(product_data_batch)
                    )
                    response = inventory_api.update_multi(product_data_batch)
                    # Magento bulk API will not raise Faults.
                    # Instead the response contains the faults as a dict
                    for i, result in enumerate(response):
                        if result is not True:
                            if result.get('isFault') is True and \
                                    result['faultCode'] == '101':
                                listing, = SaleChannelListing.search([
                                    ('product_identifier', '=', product_data_batch[i][0]),  # noqa
                                    ('channel', '=', channel.id),
                                ])
                                listing.state = 'disabled'
                                listing.save()
                            else:
                                cls.raise_user_error(
                                    'multi_inventory_update_fail',
                                    (result['faultCode'], result['faultMessage'])  # noqa
                                )


class Product:
    "Product"

    __name__ = "product.product"

    @classmethod
    def __setup__(cls):
        """
        Setup the class before adding to pool
        """
        super(Product, cls).__setup__()
        cls._error_messages.update({
            "invalid_category": 'Category "%s" must have a magento category '
                'associated',
            "invalid_product": 'Product "%s" already has a magento product '
                'associated',
            "missing_product_code": 'Product "%s" has a missing code.',
        })

    @classmethod
    def find_or_create_using_magento_data(cls, product_data):
        """
        Find or create a product template using magento data provided.
        This method looks for an existing template using the magento ID From
        data provided. If found, it returns the template found, else creates
        a new one and returns that

        :param product_data: Product Data From Magento
        :returns: Browse record of product found/created
        """
        Product = Pool().get('product.product')
        Listing = Pool().get('product.product.channel_listing')
        Channel = Pool().get('sale.channel')

        channel = Channel.get_current_magento_channel()

        products = Product.search([
            ('code', '=', product_data['sku']),
        ])
        listings = Listing.search([
            ('product.code', '=', product_data['sku']),
            ('channel', '=', channel)
        ])

        if not products:
            product = Product.create_from(channel, product_data)
        else:
            product, = products

        if not listings:
            Listing.create_from(channel, product_data)

        return product

    @classmethod
    def extract_product_values_from_data(cls, product_data):
        """
        Extract product values from the magento data, used for both
        creation/updation of product. This method can be overwritten by
        custom modules to store extra info to a product

        :param: product_data
        :returns: Dictionary of values
        """
        Channel = Pool().get('sale.channel')

        channel = Channel.get_current_magento_channel()
        values = {
            'name': product_data.get('name') or
                ('SKU: ' + product_data.get('sku')),
            'default_uom': channel.default_uom.id,
            'salable': True,
            'sale_uom': channel.default_uom.id,
        }
        if product_data['type'] in ('downloadable', 'virtual'):
            values['type'] = 'service'
        return values

    @classmethod
    def create_from(cls, channel, product_data):
        """
        Create the product for the channel
        """
        if channel.source != 'magento':
            return super(Product, cls).create_from(channel, product_data)
        return cls.create_using_magento_data(product_data)

    @classmethod
    def create_using_magento_data(cls, product_data):
        """
        Create a new product with the `product_data` from magento.This method
        also looks for the category of the product. If found, it uses that
        category to assign the product to. If no category is found, it assigns
        the product to `Unclassified Magento Product` category

        :param product_data: Product Data from Magento
        :returns: Browse record of product created
        """
        # TODO: Remove this method completely and stick to the channel API
        # The method above (create_from) should be used instead.
        Template = Pool().get('product.template')
        Category = Pool().get('product.category')

        # Get only the first category from the list of categories
        # If no category is found, put product under unclassified category
        # which is created by default data
        if product_data.get('categories'):
            category = Category.find_or_create_using_magento_id(
                int(product_data['categories'][0])
            )
        else:
            categories = Category.search([
                ('name', '=', 'Unclassified Magento Products')
            ])
            category = categories[0]

        product_template_values = cls.extract_product_values_from_data(
            product_data
        )
        product_template_values.update({
            'products': [('create', [{
                'description': product_data.get('description'),
                'code': product_data['sku'],
                'list_price': Decimal(
                    product_data.get('special_price') or
                    product_data.get('price') or
                    0.00
                ),
                'cost_price': Decimal(product_data.get('cost') or 0.00),
            }])],
            'category': category.id,
        })
        product_template, = Template.create([product_template_values])
        return product_template.products[0]

    def update_from_magento(self):
        """
        Update product using magento ID for that product

        :returns: Active record of product updated
        """
        Channel = Pool().get('sale.channel')
        SaleChannelListing = Pool().get('product.product.channel_listing')

        channel = Channel.get_current_magento_channel()

        with magento.Product(
            channel.magento_url, channel.magento_api_user,
            channel.magento_api_key
        ) as product_api:
            channel_listing, = SaleChannelListing.search([
                ('product', '=', self.id),
                ('channel', '=', channel.id),
            ])
            product_data = product_api.info(
                channel_listing.product_identifier,
                identifierType="productID"
            )

        return self.update_from_magento_using_data(product_data)

    def update_from_magento_using_data(self, product_data):
        """
        Update product using magento data

        :param product_data: Product Data from magento
        :returns: Active record of product updated
        """
        Template = Pool().get('product.template')

        product_template_values = self.extract_product_values_from_data(
            product_data
        )
        product_template_values.update({
            'products': [('write', [self], {
                'description': product_data.get('description'),
                'code': product_data['sku'],
                'list_price': Decimal(
                    product_data.get('special_price') or
                    product_data.get('price') or
                    0.00
                ),
                'cost_price': Decimal(product_data.get('cost') or 0.00),
            })]
        })
        Template.write([self.template], product_template_values)

        return self

    def get_product_values_for_export_to_magento(self, categories, channels):
        """Creates a dictionary of values which have to exported to magento for
        creating a product

        :param categories: List of Browse record of categories
        :param channels: List of Browse record of channels
        """
        return {
            'categories': map(
                lambda mag_categ: mag_categ.magento_id,
                categories[0].magento_ids
            ),
            'websites': map(lambda c: c.magento_website_id, channels),
            'name': self.name,
            'description': self.description or self.name,
            'short_description': self.description or self.name,
            'status': '1',
            'visibility': '4',
            'price': float(str(self.list_price)),
            'tax_class_id': '1',    # FIXME
        }


class ProductPriceTier(ModelSQL, ModelView):
    """Price Tiers for product

    This model stores the price tiers to be used while sending
    tier prices for a product from Tryton to Magento.
    """
    __name__ = 'product.price_tier'
    _rec_name = 'quantity'

    product_listing = fields.Many2One(
        'product.product.channel_listing', 'Product Listing', required=True,
        readonly=True,
    )
    quantity = fields.Float(
        'Quantity', required=True
    )
    price = fields.Function(fields.Numeric('Price'), 'get_price')

    @classmethod
    def __setup__(cls):
        """
        Setup the class before adding to pool
        """
        super(ProductPriceTier, cls).__setup__()
        cls._sql_constraints += [
            (
                'product_listing_quantity_unique',
                'UNIQUE(product_listing, quantity)',
                'Quantity in price tiers must be unique for a product listing'
            )
        ]

    def get_price(self, name):
        """Calculate the price of the product for quantity set in record

        :param name: Name of field
        """
        Channel = Pool().get('sale.channel')

        if not Transaction().context.get('current_channel'):
            return 0

        channel = Channel.get_current_magento_channel()
        product = self.product_listing.product
        return channel.price_list.compute(
            None, product, product.list_price, self.quantity,
            channel.default_uom
        )
