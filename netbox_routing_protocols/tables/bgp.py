import django_tables2 as tables
from django.utils.translation import gettext_lazy as _

from netbox.tables import NetBoxTable, columns

from netbox_routing_protocols.models import (
    BGPAddressFamily,
    BGPAddressFamilyRedistribute,
    BGPPeer,
    BGPPeerAddressFamily,
    BGPPeergroup,
    BGPPeergroupAddressFamily,
    BGPRouter,
)

__all__ = (
    'BGPAddressFamilyRedistributeTable',
    'BGPAddressFamilyTable',
    'BGPPeerAddressFamilyTable',
    'BGPPeergroupAddressFamilyTable',
    'BGPPeergroupTable',
    'BGPPeerTable',
    'BGPRouterTable',
)


class BGPRouterTable(NetBoxTable):
    # `name` is a property ("<device> :: <VRF>"), so it is ordered by those columns.
    name = tables.Column(
        verbose_name=_('BGP Router'),
        accessor=tables.A('name'),
        order_by=('device', 'vrf'),
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
    asn = tables.Column(
        verbose_name=_('ASN'),
        linkify=True,
    )
    router_id = tables.Column(
        verbose_name=_('Router ID'),
        linkify=True,
    )
    enable = columns.BooleanColumn(
        verbose_name=_('Enabled'),
    )
    multipath_relax = columns.BooleanColumn(
        verbose_name=_('Multipath Relax'),
    )
    route_reflection = columns.BooleanColumn(
        verbose_name=_('Route Reflection'),
    )
    enable_evpn = columns.BooleanColumn(
        verbose_name=_('Enable EVPN'),
    )
    comments = columns.MarkdownColumn(
        verbose_name=_('Comments'),
    )
    tags = columns.TagColumn(
        url_name='plugins:netbox_routing_protocols:bgprouter_list',
    )

    class Meta(NetBoxTable.Meta):
        model = BGPRouter
        fields = (
            'pk',
            'id',
            'name',
            'device',
            'vrf',
            'enable',
            'asn',
            'router_id',
            'multipath_relax',
            'route_reflection',
            'enable_evpn',
            'description',
            'comments',
            'tags',
            'created',
            'last_updated',
        )
        default_columns = ('pk', 'device', 'vrf', 'asn', 'router_id', 'enable', 'description')


class BGPPeergroupTable(NetBoxTable):
    name = tables.Column(
        verbose_name=_('Name'),
        linkify=True,
    )
    bgprouter = tables.Column(
        verbose_name=_('BGP Router'),
        linkify=True,
    )
    # `device` and `vrf` are properties reaching through the router, so both traverse the FK.
    device = tables.Column(
        verbose_name=_('Device'),
        accessor=tables.A('bgprouter__device'),
        linkify=True,
    )
    vrf = tables.Column(
        verbose_name=_('VRF'),
        accessor=tables.A('bgprouter__vrf'),
        linkify=True,
    )
    remote_as = tables.Column(
        verbose_name=_('Remote AS'),
        linkify=True,
    )
    enable = columns.BooleanColumn(
        verbose_name=_('Enabled'),
    )
    bfd = columns.BooleanColumn(
        verbose_name=_('BFD'),
    )
    ebgp_multihop = columns.BooleanColumn(
        verbose_name=_('eBGP Multihop'),
    )
    peer_count = columns.LinkedCountColumn(
        accessor=tables.A('peers__count'),
        viewname='plugins:netbox_routing_protocols:bgppeer_list',
        url_params={'peergroup_id': 'pk'},
        verbose_name=_('Peers'),
    )
    comments = columns.MarkdownColumn(
        verbose_name=_('Comments'),
    )
    tags = columns.TagColumn(
        url_name='plugins:netbox_routing_protocols:bgppeergroup_list',
    )

    class Meta(NetBoxTable.Meta):
        model = BGPPeergroup
        fields = (
            'pk',
            'id',
            'name',
            'bgprouter',
            'device',
            'vrf',
            'enable',
            'remote_as',
            'bfd',
            'ebgp_multihop',
            'ebgp_multihop_ttl',
            'peer_count',
            'description',
            'comments',
            'tags',
            'created',
            'last_updated',
        )
        default_columns = ('pk', 'name', 'device', 'vrf', 'remote_as', 'enable', 'description')


class BGPPeerTable(NetBoxTable):
    # `name` is a property (the remote address, or the interface for an unnumbered session).
    name = tables.Column(
        verbose_name=_('Peer'),
        accessor=tables.A('name'),
        order_by=('interface', 'remote_address'),
        linkify=True,
    )
    bgprouter = tables.Column(
        verbose_name=_('BGP Router'),
        linkify=True,
    )
    device = tables.Column(
        verbose_name=_('Device'),
        accessor=tables.A('bgprouter__device'),
        linkify=True,
    )
    vrf = tables.Column(
        verbose_name=_('VRF'),
        accessor=tables.A('bgprouter__vrf'),
        linkify=True,
    )
    remote_address = tables.Column(
        verbose_name=_('Remote Address'),
        linkify=True,
    )
    interface = tables.Column(
        verbose_name=_('Interface'),
        linkify=True,
    )
    peergroup = tables.Column(
        verbose_name=_('Peer Group'),
        linkify=True,
    )
    remote_as = tables.Column(
        verbose_name=_('Remote AS'),
        linkify=True,
    )
    enable = columns.BooleanColumn(
        verbose_name=_('Enabled'),
    )
    bfd = columns.BooleanColumn(
        verbose_name=_('BFD'),
    )
    ebgp_multihop = columns.BooleanColumn(
        verbose_name=_('eBGP Multihop'),
    )
    comments = columns.MarkdownColumn(
        verbose_name=_('Comments'),
    )
    tags = columns.TagColumn(
        url_name='plugins:netbox_routing_protocols:bgppeer_list',
    )

    class Meta(NetBoxTable.Meta):
        model = BGPPeer
        fields = (
            'pk',
            'id',
            'name',
            'bgprouter',
            'device',
            'vrf',
            'remote_address',
            'interface',
            'peergroup',
            'enable',
            'remote_as',
            'bfd',
            'ebgp_multihop',
            'ebgp_multihop_ttl',
            'description',
            'comments',
            'tags',
            'created',
            'last_updated',
        )
        default_columns = ('pk', 'name', 'device', 'vrf', 'peergroup', 'remote_as', 'enable', 'description')


class BGPAddressFamilyTable(NetBoxTable):
    family = columns.ChoiceFieldColumn(
        verbose_name=_('Address Family'),
        linkify=True,
    )
    bgprouter = tables.Column(
        verbose_name=_('BGP Router'),
        linkify=True,
    )
    device = tables.Column(
        verbose_name=_('Device'),
        accessor=tables.A('bgprouter__device'),
        linkify=True,
    )
    vrf = tables.Column(
        verbose_name=_('VRF'),
        accessor=tables.A('bgprouter__vrf'),
        linkify=True,
    )
    aggregate_routes = columns.ManyToManyColumn(
        verbose_name=_('Aggregate Routes'),
        linkify_item=True,
        orderable=False,
    )
    aggregate_route_map = tables.Column(
        verbose_name=_('Aggregate Route Map'),
        linkify=True,
    )
    networks = columns.ManyToManyColumn(
        verbose_name=_('Network Statements'),
        linkify_item=True,
        orderable=False,
    )
    network_route_map = tables.Column(
        verbose_name=_('Network Route Map'),
        linkify=True,
    )
    enable = columns.BooleanColumn(
        verbose_name=_('Enabled'),
    )
    export_to_evpn = columns.BooleanColumn(
        verbose_name=_('Export to EVPN'),
    )
    comments = columns.MarkdownColumn(
        verbose_name=_('Comments'),
    )
    tags = columns.TagColumn(
        url_name='plugins:netbox_routing_protocols:bgpaddressfamily_list',
    )

    class Meta(NetBoxTable.Meta):
        model = BGPAddressFamily
        fields = (
            'pk',
            'id',
            'family',
            'bgprouter',
            'device',
            'vrf',
            'enable',
            'aggregate_routes',
            'aggregate_route_map',
            'networks',
            'network_route_map',
            'export_to_evpn',
            'description',
            'comments',
            'tags',
            'created',
            'last_updated',
        )
        default_columns = ('pk', 'family', 'device', 'vrf', 'enable', 'export_to_evpn', 'description')


class BGPAddressFamilyRedistributeTable(NetBoxTable):
    protocol = columns.ChoiceFieldColumn(
        verbose_name=_('Protocol'),
        linkify=True,
    )
    family = tables.Column(
        verbose_name=_('Address Family'),
        linkify=True,
    )
    bgprouter = tables.Column(
        verbose_name=_('BGP Router'),
        accessor=tables.A('family__bgprouter'),
        linkify=True,
    )
    device = tables.Column(
        verbose_name=_('Device'),
        accessor=tables.A('family__bgprouter__device'),
        linkify=True,
    )
    vrf = tables.Column(
        verbose_name=_('VRF'),
        accessor=tables.A('family__bgprouter__vrf'),
        linkify=True,
    )
    route_map = tables.Column(
        verbose_name=_('Route Map'),
        linkify=True,
    )
    enable = columns.BooleanColumn(
        verbose_name=_('Enabled'),
    )
    comments = columns.MarkdownColumn(
        verbose_name=_('Comments'),
    )
    tags = columns.TagColumn(
        url_name='plugins:netbox_routing_protocols:bgpaddressfamilyredistribute_list',
    )

    class Meta(NetBoxTable.Meta):
        model = BGPAddressFamilyRedistribute
        fields = (
            'pk',
            'id',
            'protocol',
            'family',
            'bgprouter',
            'device',
            'vrf',
            'enable',
            'route_map',
            'description',
            'comments',
            'tags',
            'created',
            'last_updated',
        )
        default_columns = ('pk', 'protocol', 'family', 'device', 'vrf', 'enable', 'route_map')


class BGPPeerAddressFamilyTable(NetBoxTable):
    family = columns.ChoiceFieldColumn(
        verbose_name=_('Address Family'),
        linkify=True,
    )
    peer = tables.Column(
        verbose_name=_('BGP Peer'),
        linkify=True,
    )
    bgprouter = tables.Column(
        verbose_name=_('BGP Router'),
        accessor=tables.A('peer__bgprouter'),
        linkify=True,
    )
    device = tables.Column(
        verbose_name=_('Device'),
        accessor=tables.A('peer__bgprouter__device'),
        linkify=True,
    )
    vrf = tables.Column(
        verbose_name=_('VRF'),
        accessor=tables.A('peer__bgprouter__vrf'),
        linkify=True,
    )
    inbound_policy = tables.Column(
        verbose_name=_('Inbound Policy'),
        linkify=True,
    )
    outbound_policy = tables.Column(
        verbose_name=_('Outbound Policy'),
        linkify=True,
    )
    enable = columns.BooleanColumn(
        verbose_name=_('Enabled'),
    )
    soft_reconfiguration = columns.BooleanColumn(
        verbose_name=_('Soft Reconfiguration'),
    )
    default_originate = columns.BooleanColumn(
        verbose_name=_('Default Originate'),
    )
    route_reflector_client = columns.BooleanColumn(
        verbose_name=_('Route Reflector Client'),
    )
    comments = columns.MarkdownColumn(
        verbose_name=_('Comments'),
    )
    tags = columns.TagColumn(
        url_name='plugins:netbox_routing_protocols:bgppeeraddressfamily_list',
    )

    class Meta(NetBoxTable.Meta):
        model = BGPPeerAddressFamily
        fields = (
            'pk',
            'id',
            'family',
            'peer',
            'bgprouter',
            'device',
            'vrf',
            'enable',
            'inbound_policy',
            'outbound_policy',
            'soft_reconfiguration',
            'default_originate',
            'route_reflector_client',
            'description',
            'comments',
            'tags',
            'created',
            'last_updated',
        )
        default_columns = ('pk', 'peer', 'family', 'device', 'enable', 'inbound_policy', 'outbound_policy')


class BGPPeergroupAddressFamilyTable(NetBoxTable):
    family = columns.ChoiceFieldColumn(
        verbose_name=_('Address Family'),
        linkify=True,
    )
    peergroup = tables.Column(
        verbose_name=_('BGP Peer Group'),
        linkify=True,
    )
    bgprouter = tables.Column(
        verbose_name=_('BGP Router'),
        accessor=tables.A('peergroup__bgprouter'),
        linkify=True,
    )
    device = tables.Column(
        verbose_name=_('Device'),
        accessor=tables.A('peergroup__bgprouter__device'),
        linkify=True,
    )
    vrf = tables.Column(
        verbose_name=_('VRF'),
        accessor=tables.A('peergroup__bgprouter__vrf'),
        linkify=True,
    )
    inbound_policy = tables.Column(
        verbose_name=_('Inbound Policy'),
        linkify=True,
    )
    outbound_policy = tables.Column(
        verbose_name=_('Outbound Policy'),
        linkify=True,
    )
    enable = columns.BooleanColumn(
        verbose_name=_('Enabled'),
    )
    soft_reconfiguration = columns.BooleanColumn(
        verbose_name=_('Soft Reconfiguration'),
    )
    default_originate = columns.BooleanColumn(
        verbose_name=_('Default Originate'),
    )
    route_reflector_client = columns.BooleanColumn(
        verbose_name=_('Route Reflector Client'),
    )
    comments = columns.MarkdownColumn(
        verbose_name=_('Comments'),
    )
    tags = columns.TagColumn(
        url_name='plugins:netbox_routing_protocols:bgppeergroupaddressfamily_list',
    )

    class Meta(NetBoxTable.Meta):
        model = BGPPeergroupAddressFamily
        fields = (
            'pk',
            'id',
            'family',
            'peergroup',
            'bgprouter',
            'device',
            'vrf',
            'enable',
            'inbound_policy',
            'outbound_policy',
            'soft_reconfiguration',
            'default_originate',
            'route_reflector_client',
            'description',
            'comments',
            'tags',
            'created',
            'last_updated',
        )
        default_columns = ('pk', 'peergroup', 'family', 'device', 'enable', 'inbound_policy', 'outbound_policy')
