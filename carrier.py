# -*- coding: utf-8 -*-
from trytond.pool import PoolMeta


__metaclass__ = PoolMeta
__all__ = [
    'SaleChannelCarrier',
]


class SaleChannelCarrier:
    __name__ = 'sale.channel.carrier'

    def get_magento_mapping(self):
        """
        Return code and title for magento

        Downstream modules can override this behaviour

        Return: (`code`, `title`)
        """
        return self.code, self.title
