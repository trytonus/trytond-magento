# -*- coding: utf-8 -*-
from trytond.pool import PoolMeta
from trytond.model import fields, ModelSQL, ModelView
from trytond.transaction import Transaction

__metaclass__ = PoolMeta
__all__ = ['MagentoPaymentGateway', 'Payment']


class MagentoPaymentGateway(ModelSQL, ModelView):
    """
    This model maps the available payment gateways from magento to tryton.
    """
    __name__ = 'magento.instance.payment_gateway'
    _rec_name = 'title'

    name = fields.Char("Name", required=True, select=True)
    title = fields.Char('Title', required=True, select=True)
    gateway = fields.Many2One(
        'payment_gateway.gateway', 'Gateway', required=True,
        ondelete='RESTRICT', select=True,
    )
    channel = fields.Many2One(
        'sale.channel', 'Magento Channel', readonly=True, select=True,
        domain=[('source', '=', 'magento')]
    )

    @classmethod
    def __setup__(cls):
        """
        Setup the class before adding to pool
        """
        super(MagentoPaymentGateway, cls).__setup__()
        cls._sql_constraints += [
            (
                'name_channel_unique', 'unique(name, channel)',
                'Payment gateway already exist for this channel'
            )
        ]

    @classmethod
    def create_all_using_magento_data(cls, magento_data):
        """
        Creates record for list of payment gateways sent by magento.
        It creates a new gateway only if one with the same name does not
        exist for this channel.
        """
        gateways = []
        for data in magento_data:
            gateway = cls.find_using_magento_data(data)
            if gateway:
                gateways.append(gateway)
            else:
                gateways.append(cls.create_using_magento_data(data))
        return gateways

    @classmethod
    def create_using_magento_data(cls, gateway_data):
        """
        Create record for gateway data sent by magento
        """
        raise NotImplementedError

    @classmethod
    def find_using_magento_data(cls, gateway_data):
        """
        Search for an existing gateway by matching name and channel.
        If found, return its active record else None
        """
        try:
            gateway, = cls.search([
                ('name', '=', gateway_data['name']),
                ('channel', '=', Transaction().context['current_channel']),
            ])
        except ValueError:
            return None
        else:
            return gateway


class Payment:
    __name__ = "sale.payment"

    magento_id = fields.Integer('Magento ID', readonly=True)

    @classmethod
    def __setup__(cls):
        """
        Setup the class before adding to pool
        """
        super(Payment, cls).__setup__()
        # TODO: Add validation to make sure payment magento id per channel
        # is unique!
