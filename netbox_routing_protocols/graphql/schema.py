"""
GraphQL query fields contributed by this plugin.

NetBox merges every registered plugin ``Query`` class into its own root
``Query`` type, so field names share a single namespace with the core apps.
``prefix_list`` is already taken by IPAM (it is the list field for
``ipam.Prefix``), so this plugin's PrefixList model is queried as
``ip_prefix_list`` / ``ip_prefix_list_list``. Every other field is named after
its model.
"""

import strawberry
import strawberry_django

from .types import (
    BFDProfileType,
    BGPAddressFamilyRedistributeType,
    BGPAddressFamilyType,
    BGPPeerAddressFamilyType,
    BGPPeergroupAddressFamilyType,
    BGPPeergroupType,
    BGPPeerType,
    BGPRouterType,
    PrefixListRuleType,
    PrefixListType,
    RouteMapRuleType,
    RouteMapType,
    StaticRouteType,
)

__all__ = ('Query',)


@strawberry.type(name='Query')
class Query:
    static_route: StaticRouteType = strawberry_django.field()
    static_route_list: list[StaticRouteType] = strawberry_django.field()

    ip_prefix_list: PrefixListType = strawberry_django.field()
    ip_prefix_list_list: list[PrefixListType] = strawberry_django.field()

    prefix_list_rule: PrefixListRuleType = strawberry_django.field()
    prefix_list_rule_list: list[PrefixListRuleType] = strawberry_django.field()

    route_map: RouteMapType = strawberry_django.field()
    route_map_list: list[RouteMapType] = strawberry_django.field()

    route_map_rule: RouteMapRuleType = strawberry_django.field()
    route_map_rule_list: list[RouteMapRuleType] = strawberry_django.field()

    bfd_profile: BFDProfileType = strawberry_django.field()
    bfd_profile_list: list[BFDProfileType] = strawberry_django.field()

    bgp_router: BGPRouterType = strawberry_django.field()
    bgp_router_list: list[BGPRouterType] = strawberry_django.field()

    bgp_peergroup: BGPPeergroupType = strawberry_django.field()
    bgp_peergroup_list: list[BGPPeergroupType] = strawberry_django.field()

    bgp_peer: BGPPeerType = strawberry_django.field()
    bgp_peer_list: list[BGPPeerType] = strawberry_django.field()

    bgp_address_family: BGPAddressFamilyType = strawberry_django.field()
    bgp_address_family_list: list[BGPAddressFamilyType] = strawberry_django.field()

    bgp_address_family_redistribute: BGPAddressFamilyRedistributeType = strawberry_django.field()
    bgp_address_family_redistribute_list: list[BGPAddressFamilyRedistributeType] = strawberry_django.field()

    bgp_peer_address_family: BGPPeerAddressFamilyType = strawberry_django.field()
    bgp_peer_address_family_list: list[BGPPeerAddressFamilyType] = strawberry_django.field()

    bgp_peergroup_address_family: BGPPeergroupAddressFamilyType = strawberry_django.field()
    bgp_peergroup_address_family_list: list[BGPPeergroupAddressFamilyType] = strawberry_django.field()
