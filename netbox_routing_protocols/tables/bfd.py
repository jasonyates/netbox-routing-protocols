import django_tables2 as tables
from django.utils.translation import gettext_lazy as _

from netbox.tables import NetBoxTable, columns

from netbox_routing_protocols.models import BFDProfile

__all__ = ('BFDProfileTable',)


class BFDProfileTable(NetBoxTable):
    name = tables.Column(
        verbose_name=_('Name'),
        linkify=True,
    )
    device = tables.Column(
        verbose_name=_('Device'),
        linkify=True,
    )
    echo_mode = columns.BooleanColumn(
        verbose_name=_('Echo Mode'),
    )
    passive_mode = columns.BooleanColumn(
        verbose_name=_('Passive Mode'),
    )
    comments = columns.MarkdownColumn(
        verbose_name=_('Comments'),
    )
    tags = columns.TagColumn(
        url_name='plugins:netbox_routing_protocols:bfdprofile_list',
    )

    class Meta(NetBoxTable.Meta):
        model = BFDProfile
        fields = (
            'pk',
            'id',
            'name',
            'device',
            'min_tx',
            'min_rx',
            'detect_multiplier',
            'echo_mode',
            'echo_tx',
            'echo_rx',
            'passive_mode',
            'minimum_ttl',
            'description',
            'comments',
            'tags',
            'created',
            'last_updated',
        )
        default_columns = ('pk', 'name', 'device', 'min_tx', 'min_rx', 'detect_multiplier', 'description')
