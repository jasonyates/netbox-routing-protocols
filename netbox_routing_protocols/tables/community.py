import django_tables2 as tables
from django.utils.translation import gettext_lazy as _

from netbox.tables import NetBoxTable, columns

from netbox_routing_protocols.models import BGPCommunity, BGPCommunityList, BGPCommunityListRule

__all__ = (
    'BGPCommunityListRuleTable',
    'BGPCommunityListTable',
    'BGPCommunityTable',
)


class BGPCommunityTable(NetBoxTable):
    value = tables.Column(
        verbose_name=_('Value'),
        linkify=True,
    )
    type = columns.ChoiceFieldColumn(
        verbose_name=_('Type'),
    )
    comments = columns.MarkdownColumn(
        verbose_name=_('Comments'),
    )
    tags = columns.TagColumn(
        url_name='plugins:netbox_routing_protocols:bgpcommunity_list',
    )

    class Meta(NetBoxTable.Meta):
        model = BGPCommunity
        fields = (
            'pk',
            'id',
            'value',
            'type',
            'name',
            'description',
            'comments',
            'tags',
            'created',
            'last_updated',
        )
        default_columns = ('pk', 'value', 'type', 'name', 'description')


class BGPCommunityListTable(NetBoxTable):
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
        viewname='plugins:netbox_routing_protocols:bgpcommunitylistrule_list',
        url_params={'community_list_id': 'pk'},
        verbose_name=_('Rules'),
    )
    comments = columns.MarkdownColumn(
        verbose_name=_('Comments'),
    )
    tags = columns.TagColumn(
        url_name='plugins:netbox_routing_protocols:bgpcommunitylist_list',
    )

    class Meta(NetBoxTable.Meta):
        model = BGPCommunityList
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
        default_columns = ('pk', 'name', 'device', 'rule_count', 'description')


class BGPCommunityListRuleTable(NetBoxTable):
    # `name` is a property ("<community list> <sequence>"), so it is ordered by those columns.
    name = tables.Column(
        verbose_name=_('Rule'),
        accessor=tables.A('name'),
        order_by=('community_list', 'sequence'),
        linkify=True,
    )
    community_list = tables.Column(
        verbose_name=_('Community List'),
        linkify=True,
    )
    device = tables.Column(
        verbose_name=_('Device'),
        accessor=tables.A('community_list__device'),
        linkify=True,
    )
    sequence = tables.Column(
        verbose_name=_('Sequence'),
    )
    action = columns.ChoiceFieldColumn(
        verbose_name=_('Action'),
    )
    community = tables.Column(
        verbose_name=_('Community'),
        linkify=True,
    )
    comments = columns.MarkdownColumn(
        verbose_name=_('Comments'),
    )
    tags = columns.TagColumn(
        url_name='plugins:netbox_routing_protocols:bgpcommunitylistrule_list',
    )

    class Meta(NetBoxTable.Meta):
        model = BGPCommunityListRule
        fields = (
            'pk',
            'id',
            'name',
            'device',
            'community_list',
            'sequence',
            'action',
            'community',
            'description',
            'comments',
            'tags',
            'created',
            'last_updated',
        )
        default_columns = ('pk', 'community_list', 'sequence', 'action', 'community', 'description')
