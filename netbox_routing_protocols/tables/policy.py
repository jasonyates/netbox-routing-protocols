import django_tables2 as tables
from django.utils.translation import gettext_lazy as _

from netbox.tables import NetBoxTable, columns

from netbox_routing_protocols.models import PrefixList, PrefixListRule, RouteMap, RouteMapRule

__all__ = (
    'PrefixListRuleTable',
    'PrefixListTable',
    'RouteMapRuleTable',
    'RouteMapTable',
)


class PrefixListTable(NetBoxTable):
    name = tables.Column(
        verbose_name=_('Name'),
        linkify=True,
    )
    device = tables.Column(
        verbose_name=_('Device'),
        linkify=True,
    )
    address_family = columns.ChoiceFieldColumn(
        verbose_name=_('Address Family'),
    )
    rule_count = columns.LinkedCountColumn(
        accessor=tables.A('rules__count'),
        viewname='plugins:netbox_routing_protocols:prefixlistrule_list',
        url_params={'prefix_list_id': 'pk'},
        verbose_name=_('Rules'),
    )
    comments = columns.MarkdownColumn(
        verbose_name=_('Comments'),
    )
    tags = columns.TagColumn(
        url_name='plugins:netbox_routing_protocols:prefixlist_list',
    )

    class Meta(NetBoxTable.Meta):
        model = PrefixList
        fields = (
            'pk',
            'id',
            'name',
            'device',
            'address_family',
            'rule_count',
            'description',
            'comments',
            'tags',
            'created',
            'last_updated',
        )
        default_columns = ('pk', 'name', 'device', 'address_family', 'description')


class PrefixListRuleTable(NetBoxTable):
    # `name` is a property ("<prefix list> <sequence>"), so it is ordered by those columns.
    name = tables.Column(
        verbose_name=_('Rule'),
        accessor=tables.A('name'),
        order_by=('prefix_list', 'sequence'),
        linkify=True,
    )
    prefix_list = tables.Column(
        verbose_name=_('Prefix List'),
        linkify=True,
    )
    device = tables.Column(
        verbose_name=_('Device'),
        accessor=tables.A('prefix_list__device'),
        linkify=True,
    )
    sequence = tables.Column(
        verbose_name=_('Sequence'),
    )
    action = columns.ChoiceFieldColumn(
        verbose_name=_('Action'),
    )
    prefix = tables.Column(
        verbose_name=_('Prefix'),
        linkify=True,
    )
    match_any = columns.BooleanColumn(
        verbose_name=_('Match Any'),
    )
    match_default = columns.BooleanColumn(
        verbose_name=_('Match Default'),
    )
    comments = columns.MarkdownColumn(
        verbose_name=_('Comments'),
    )
    tags = columns.TagColumn(
        url_name='plugins:netbox_routing_protocols:prefixlistrule_list',
    )

    class Meta(NetBoxTable.Meta):
        model = PrefixListRule
        fields = (
            'pk',
            'id',
            'name',
            'device',
            'prefix_list',
            'sequence',
            'action',
            'prefix',
            'min_prefix_length',
            'max_prefix_length',
            'match_any',
            'match_default',
            'description',
            'comments',
            'tags',
            'created',
            'last_updated',
        )
        default_columns = ('pk', 'prefix_list', 'sequence', 'action', 'prefix', 'description')


class RouteMapTable(NetBoxTable):
    name = tables.Column(
        verbose_name=_('Name'),
        linkify=True,
    )
    device = tables.Column(
        verbose_name=_('Device'),
        linkify=True,
    )
    rule_count = columns.LinkedCountColumn(
        accessor=tables.A('rules__count'),
        viewname='plugins:netbox_routing_protocols:routemaprule_list',
        url_params={'route_map_id': 'pk'},
        verbose_name=_('Rules'),
    )
    comments = columns.MarkdownColumn(
        verbose_name=_('Comments'),
    )
    tags = columns.TagColumn(
        url_name='plugins:netbox_routing_protocols:routemap_list',
    )

    class Meta(NetBoxTable.Meta):
        model = RouteMap
        fields = (
            'pk',
            'id',
            'name',
            'device',
            'rule_count',
            'description',
            'comments',
            'tags',
            'created',
            'last_updated',
        )
        default_columns = ('pk', 'name', 'device', 'description')


class RouteMapRuleTable(NetBoxTable):
    # `name` is a property ("<route map> <sequence>"), so it is ordered by those columns.
    name = tables.Column(
        verbose_name=_('Rule'),
        accessor=tables.A('name'),
        order_by=('route_map', 'sequence'),
        linkify=True,
    )
    route_map = tables.Column(
        verbose_name=_('Route Map'),
        linkify=True,
    )
    device = tables.Column(
        verbose_name=_('Device'),
        accessor=tables.A('route_map__device'),
        linkify=True,
    )
    sequence = tables.Column(
        verbose_name=_('Sequence'),
    )
    action = columns.ChoiceFieldColumn(
        verbose_name=_('Action'),
    )
    prefix_list = tables.Column(
        verbose_name=_('Match Prefix List'),
        linkify=True,
    )
    match_any = columns.BooleanColumn(
        verbose_name=_('Match Any'),
    )
    comments = columns.MarkdownColumn(
        verbose_name=_('Comments'),
    )
    tags = columns.TagColumn(
        url_name='plugins:netbox_routing_protocols:routemaprule_list',
    )

    class Meta(NetBoxTable.Meta):
        model = RouteMapRule
        fields = (
            'pk',
            'id',
            'name',
            'device',
            'route_map',
            'sequence',
            'action',
            'prefix_list',
            'match_any',
            'description',
            'comments',
            'tags',
            'created',
            'last_updated',
        )
        default_columns = ('pk', 'route_map', 'sequence', 'action', 'prefix_list', 'description')
