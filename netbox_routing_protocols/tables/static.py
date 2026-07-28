import django_tables2 as tables
from django.utils.translation import gettext_lazy as _

from netbox.tables import NetBoxTable, columns

from netbox_routing_protocols.models import StaticRoute

__all__ = ('StaticRouteTable',)


class StaticRouteTable(NetBoxTable):
    # `name` is a property (the prefix, or the default route for the next hop's family), so it is
    # ordered by the underlying columns rather than in Python.
    name = tables.Column(
        verbose_name=_('Route'),
        accessor=tables.A('name'),
        order_by=('prefix', 'default_route'),
        linkify=True,
    )
    device = tables.Column(
        verbose_name=_('Device'),
        linkify=True,
    )
    vrf = tables.Column(
        verbose_name=_('VRF'),
        linkify=True,
    )
    prefix = tables.Column(
        verbose_name=_('Prefix'),
        linkify=True,
    )
    nexthop = tables.Column(
        verbose_name=_('Next Hop'),
        linkify=True,
    )
    default_route = columns.BooleanColumn(
        verbose_name=_('Default Route'),
    )
    comments = columns.MarkdownColumn(
        verbose_name=_('Comments'),
    )
    tags = columns.TagColumn(
        url_name='plugins:netbox_routing_protocols:staticroute_list',
    )

    class Meta(NetBoxTable.Meta):
        model = StaticRoute
        fields = (
            'pk',
            'id',
            'name',
            'device',
            'vrf',
            'prefix',
            'default_route',
            'nexthop',
            'description',
            'comments',
            'tags',
            'created',
            'last_updated',
        )
        default_columns = ('pk', 'name', 'device', 'vrf', 'nexthop', 'description')
