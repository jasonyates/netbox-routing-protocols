"""
Global search indexes.

NetBox imports ``<plugin>.search.indexes`` automatically, so the ``indexes``
list at the bottom of this module is all that is required to register these.

Only concrete model fields may be listed in ``fields`` or ``display_attrs``:
``display_attrs`` is resolved through ``Model._meta.get_field()``, which raises
for anything that is not a real field. Several models here identify themselves
through a Python ``name`` property (StaticRoute, PrefixListRule, RouteMapRule,
BGPPeer), so the columns behind those properties are indexed instead.

Weights follow the NetBox convention: lower is more relevant.
"""

from netbox.search import SearchIndex

from netbox_routing_protocols.models import (
    BFDProfile,
    BGPAddressFamily,
    BGPAddressFamilyRedistribute,
    BGPPeer,
    BGPPeerAddressFamily,
    BGPPeergroup,
    BGPPeergroupAddressFamily,
    BGPRouter,
    PrefixList,
    PrefixListRule,
    RouteMap,
    RouteMapRule,
    StaticRoute,
)

__all__ = (
    'BFDProfileIndex',
    'BGPAddressFamilyIndex',
    'BGPAddressFamilyRedistributeIndex',
    'BGPPeerAddressFamilyIndex',
    'BGPPeerIndex',
    'BGPPeergroupAddressFamilyIndex',
    'BGPPeergroupIndex',
    'BGPRouterIndex',
    'PrefixListIndex',
    'PrefixListRuleIndex',
    'RouteMapIndex',
    'RouteMapRuleIndex',
    'StaticRouteIndex',
    'indexes',
)


class BFDProfileIndex(SearchIndex):
    model = BFDProfile
    fields = (
        ('name', 100),
        ('description', 500),
        ('comments', 5000),
    )
    display_attrs = ('device', 'description')


class StaticRouteIndex(SearchIndex):
    # StaticRoute.name is a property derived from prefix/nexthop, so the two
    # foreign keys are indexed in its place. Both stringify to the address.
    model = StaticRoute
    fields = (
        ('prefix', 100),
        ('nexthop', 110),
        ('description', 500),
        ('comments', 5000),
    )
    display_attrs = ('device', 'vrf', 'prefix', 'nexthop', 'description')


class PrefixListIndex(SearchIndex):
    model = PrefixList
    fields = (
        ('name', 100),
        ('description', 500),
        ('comments', 5000),
    )
    display_attrs = ('device', 'address_family', 'description')


class PrefixListRuleIndex(SearchIndex):
    # PrefixListRule.name is "<prefix list> <sequence>"; sequence is the only
    # part of that which is a real column.
    model = PrefixListRule
    fields = (
        ('prefix', 100),
        ('action', 1000),
        ('sequence', 2000),
        ('description', 500),
        ('comments', 5000),
    )
    display_attrs = ('prefix_list', 'sequence', 'action', 'prefix', 'description')


class RouteMapIndex(SearchIndex):
    model = RouteMap
    fields = (
        ('name', 100),
        ('description', 500),
        ('comments', 5000),
    )
    display_attrs = ('device', 'description')


class RouteMapRuleIndex(SearchIndex):
    # As above: RouteMapRule.name is "<route map> <sequence>".
    model = RouteMapRule
    fields = (
        ('action', 1000),
        ('sequence', 2000),
        ('description', 500),
        ('comments', 5000),
    )
    display_attrs = ('route_map', 'sequence', 'action', 'prefix_list', 'description')


class BGPRouterIndex(SearchIndex):
    # BGPRouter.name is "<device> :: <vrf>", both of which are foreign keys.
    model = BGPRouter
    fields = (
        ('device', 100),
        ('vrf', 110),
        ('asn', 200),
        ('router_id', 300),
        ('description', 500),
        ('comments', 5000),
    )
    display_attrs = ('device', 'vrf', 'asn', 'router_id', 'description')


class BGPPeergroupIndex(SearchIndex):
    model = BGPPeergroup
    fields = (
        ('name', 100),
        ('remote_as', 300),
        ('description', 500),
        ('comments', 5000),
    )
    # 'device' and 'vrf' are properties on this model, so the router is shown instead.
    display_attrs = ('bgprouter', 'remote_as', 'description')


class BGPPeerIndex(SearchIndex):
    # BGPPeer.name is the interface name or the remote address, depending on
    # whether the session is unnumbered. Index both underlying columns.
    model = BGPPeer
    fields = (
        ('remote_address', 100),
        ('interface', 110),
        ('remote_as', 300),
        ('description', 500),
        ('comments', 5000),
    )
    display_attrs = ('bgprouter', 'remote_address', 'interface', 'peergroup', 'remote_as', 'description')


class BGPAddressFamilyIndex(SearchIndex):
    model = BGPAddressFamily
    fields = (
        ('family', 100),
        ('description', 500),
        ('comments', 5000),
    )
    display_attrs = ('bgprouter', 'family', 'description')


class BGPAddressFamilyRedistributeIndex(SearchIndex):
    model = BGPAddressFamilyRedistribute
    fields = (
        ('protocol', 100),
        ('description', 500),
        ('comments', 5000),
    )
    display_attrs = ('family', 'protocol', 'route_map', 'description')


class BGPPeerAddressFamilyIndex(SearchIndex):
    model = BGPPeerAddressFamily
    fields = (
        ('family', 100),
        ('description', 500),
        ('comments', 5000),
    )
    display_attrs = ('peer', 'family', 'description')


class BGPPeergroupAddressFamilyIndex(SearchIndex):
    model = BGPPeergroupAddressFamily
    fields = (
        ('family', 100),
        ('description', 500),
        ('comments', 5000),
    )
    display_attrs = ('peergroup', 'family', 'description')


indexes = [
    StaticRouteIndex,
    BFDProfileIndex,
    PrefixListIndex,
    PrefixListRuleIndex,
    RouteMapIndex,
    RouteMapRuleIndex,
    BGPRouterIndex,
    BGPPeergroupIndex,
    BGPPeerIndex,
    BGPAddressFamilyIndex,
    BGPAddressFamilyRedistributeIndex,
    BGPPeerAddressFamilyIndex,
    BGPPeergroupAddressFamilyIndex,
]
