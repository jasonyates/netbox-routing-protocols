"""
Strawberry filter types for the GraphQL API.

NetBox has used Strawberry (not Graphene) since 4.0. Each filter is declared
with ``@strawberry_django.filter_type(Model, lookups=True)`` and derives from
``PrimaryModelFilter``, which supplies id/tags/custom-field/change-logging
lookups plus ``description`` and ``comments``.

Note the NetBox 4.5+ filter syntax: scalar fields are wrapped in a lookup type
(``{name: {i_contains: "x"}}``), choice fields in ``BaseFilterLookup`` over an
enum (``{action: {exact: PERMIT}}``), and ``*_id`` fields take a bare ID.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING, Annotated

import strawberry
import strawberry_django
from strawberry import ID
from strawberry_django import BaseFilterLookup, FilterLookup, StrFilterLookup

from netbox.graphql.filters import PrimaryModelFilter

from netbox_routing_protocols import models
from netbox_routing_protocols.choices import (
    ActionChoices,
    AddressFamilyChoices,
    BGPAddressFamilyChoices,
    BGPRedistributeProtocolChoices,
)

if TYPE_CHECKING:
    from dcim.graphql.filters import DeviceFilter, InterfaceFilter
    from ipam.graphql.filters import ASNFilter, IPAddressFilter, PrefixFilter, VRFFilter
    from netbox.graphql.filter_lookups import IntegerLookup

__all__ = (
    'BGPAddressFamilyEnum',
    'BGPAddressFamilyFilter',
    'BGPAddressFamilyRedistributeFilter',
    'BGPPeerAddressFamilyFilter',
    'BGPPeerFilter',
    'BGPPeergroupAddressFamilyFilter',
    'BGPPeergroupFilter',
    'BGPRedistributeProtocolEnum',
    'BGPRouterFilter',
    'PolicyActionEnum',
    'PrefixListAddressFamilyEnum',
    'PrefixListFilter',
    'PrefixListRuleFilter',
    'RouteMapFilter',
    'RouteMapRuleFilter',
    'StaticRouteFilter',
)

#
# Enums
#
# Explicit names are given so these cannot collide with a core NetBox enum, and
# a prefix is required because ChoiceSet.as_enum() builds member names from the
# raw values — AddressFamilyChoices stores integers, which are not valid
# identifiers on their own.
#

PolicyActionEnum = strawberry.enum(ActionChoices.as_enum(name='PolicyActionEnum', prefix='action'))
PrefixListAddressFamilyEnum = strawberry.enum(
    AddressFamilyChoices.as_enum(name='PrefixListAddressFamilyEnum', prefix='family')
)
BGPAddressFamilyEnum = strawberry.enum(BGPAddressFamilyChoices.as_enum(name='BGPAddressFamilyEnum', prefix='family'))
BGPRedistributeProtocolEnum = strawberry.enum(
    BGPRedistributeProtocolChoices.as_enum(name='BGPRedistributeProtocolEnum', prefix='protocol')
)


#
# Static routing
#


@strawberry_django.filter_type(models.StaticRoute, lookups=True)
class StaticRouteFilter(PrimaryModelFilter):
    device: Annotated['DeviceFilter', strawberry.lazy('dcim.graphql.filters')] | None = strawberry_django.filter_field()
    device_id: ID | None = strawberry_django.filter_field()
    vrf: Annotated['VRFFilter', strawberry.lazy('ipam.graphql.filters')] | None = strawberry_django.filter_field()
    vrf_id: ID | None = strawberry_django.filter_field()
    prefix: Annotated['PrefixFilter', strawberry.lazy('ipam.graphql.filters')] | None = strawberry_django.filter_field()
    prefix_id: ID | None = strawberry_django.filter_field()
    nexthop: Annotated['IPAddressFilter', strawberry.lazy('ipam.graphql.filters')] | None = (
        strawberry_django.filter_field()
    )
    nexthop_id: ID | None = strawberry_django.filter_field()
    default_route: FilterLookup[bool] | None = strawberry_django.filter_field()


#
# Routing policy
#


@strawberry_django.filter_type(models.PrefixList, lookups=True)
class PrefixListFilter(PrimaryModelFilter):
    name: StrFilterLookup | None = strawberry_django.filter_field()
    device: Annotated['DeviceFilter', strawberry.lazy('dcim.graphql.filters')] | None = strawberry_django.filter_field()
    device_id: ID | None = strawberry_django.filter_field()
    address_family: BaseFilterLookup[PrefixListAddressFamilyEnum] | None = strawberry_django.filter_field()


@strawberry_django.filter_type(models.PrefixListRule, lookups=True)
class PrefixListRuleFilter(PrimaryModelFilter):
    prefix_list: Annotated['PrefixListFilter', strawberry.lazy('netbox_routing_protocols.graphql.filters')] | None = (
        strawberry_django.filter_field()
    )
    prefix_list_id: ID | None = strawberry_django.filter_field()
    sequence: Annotated['IntegerLookup', strawberry.lazy('netbox.graphql.filter_lookups')] | None = (
        strawberry_django.filter_field()
    )
    action: BaseFilterLookup[PolicyActionEnum] | None = strawberry_django.filter_field()
    prefix: Annotated['PrefixFilter', strawberry.lazy('ipam.graphql.filters')] | None = strawberry_django.filter_field()
    prefix_id: ID | None = strawberry_django.filter_field()
    match_default: FilterLookup[bool] | None = strawberry_django.filter_field()
    match_any: FilterLookup[bool] | None = strawberry_django.filter_field()
    min_prefix_length: Annotated['IntegerLookup', strawberry.lazy('netbox.graphql.filter_lookups')] | None = (
        strawberry_django.filter_field()
    )
    max_prefix_length: Annotated['IntegerLookup', strawberry.lazy('netbox.graphql.filter_lookups')] | None = (
        strawberry_django.filter_field()
    )


@strawberry_django.filter_type(models.RouteMap, lookups=True)
class RouteMapFilter(PrimaryModelFilter):
    name: StrFilterLookup | None = strawberry_django.filter_field()
    device: Annotated['DeviceFilter', strawberry.lazy('dcim.graphql.filters')] | None = strawberry_django.filter_field()
    device_id: ID | None = strawberry_django.filter_field()


@strawberry_django.filter_type(models.RouteMapRule, lookups=True)
class RouteMapRuleFilter(PrimaryModelFilter):
    route_map: Annotated['RouteMapFilter', strawberry.lazy('netbox_routing_protocols.graphql.filters')] | None = (
        strawberry_django.filter_field()
    )
    route_map_id: ID | None = strawberry_django.filter_field()
    sequence: Annotated['IntegerLookup', strawberry.lazy('netbox.graphql.filter_lookups')] | None = (
        strawberry_django.filter_field()
    )
    action: BaseFilterLookup[PolicyActionEnum] | None = strawberry_django.filter_field()
    prefix_list: Annotated['PrefixListFilter', strawberry.lazy('netbox_routing_protocols.graphql.filters')] | None = (
        strawberry_django.filter_field()
    )
    prefix_list_id: ID | None = strawberry_django.filter_field()
    match_any: FilterLookup[bool] | None = strawberry_django.filter_field()


#
# BGP
#


@strawberry_django.filter_type(models.BGPRouter, lookups=True)
class BGPRouterFilter(PrimaryModelFilter):
    device: Annotated['DeviceFilter', strawberry.lazy('dcim.graphql.filters')] | None = strawberry_django.filter_field()
    device_id: ID | None = strawberry_django.filter_field()
    vrf: Annotated['VRFFilter', strawberry.lazy('ipam.graphql.filters')] | None = strawberry_django.filter_field()
    vrf_id: ID | None = strawberry_django.filter_field()
    enable: FilterLookup[bool] | None = strawberry_django.filter_field()
    asn: Annotated['ASNFilter', strawberry.lazy('ipam.graphql.filters')] | None = strawberry_django.filter_field()
    asn_id: ID | None = strawberry_django.filter_field()
    router_id: Annotated['IPAddressFilter', strawberry.lazy('ipam.graphql.filters')] | None = (
        strawberry_django.filter_field()
    )
    aspath_ignore: FilterLookup[bool] | None = strawberry_django.filter_field()
    route_reflection: FilterLookup[bool] | None = strawberry_django.filter_field()
    enable_evpn: FilterLookup[bool] | None = strawberry_django.filter_field()


@dataclass
class BGPPeerAttributesFilterMixin:
    """
    Session attributes shared by BGPPeer and BGPPeergroup.

    `device` and `vrf` are Python properties on these models rather than
    columns, so they are exposed by traversing `bgprouter` instead.
    """

    bgprouter: Annotated['BGPRouterFilter', strawberry.lazy('netbox_routing_protocols.graphql.filters')] | None = (
        strawberry_django.filter_field()
    )
    bgprouter_id: ID | None = strawberry_django.filter_field()
    enable: FilterLookup[bool] | None = strawberry_django.filter_field()
    remote_as: Annotated['ASNFilter', strawberry.lazy('ipam.graphql.filters')] | None = strawberry_django.filter_field()
    remote_as_id: ID | None = strawberry_django.filter_field()
    bfd: FilterLookup[bool] | None = strawberry_django.filter_field()
    ebgp_multihop: FilterLookup[bool] | None = strawberry_django.filter_field()
    ebgp_multihop_ttl: Annotated['IntegerLookup', strawberry.lazy('netbox.graphql.filter_lookups')] | None = (
        strawberry_django.filter_field()
    )


@strawberry_django.filter_type(models.BGPPeergroup, lookups=True)
class BGPPeergroupFilter(BGPPeerAttributesFilterMixin, PrimaryModelFilter):
    name: StrFilterLookup | None = strawberry_django.filter_field()


@strawberry_django.filter_type(models.BGPPeer, lookups=True)
class BGPPeerFilter(BGPPeerAttributesFilterMixin, PrimaryModelFilter):
    remote_address: Annotated['IPAddressFilter', strawberry.lazy('ipam.graphql.filters')] | None = (
        strawberry_django.filter_field()
    )
    remote_address_id: ID | None = strawberry_django.filter_field()
    interface: Annotated['InterfaceFilter', strawberry.lazy('dcim.graphql.filters')] | None = (
        strawberry_django.filter_field()
    )
    interface_id: ID | None = strawberry_django.filter_field()
    peergroup: Annotated['BGPPeergroupFilter', strawberry.lazy('netbox_routing_protocols.graphql.filters')] | None = (
        strawberry_django.filter_field()
    )
    peergroup_id: ID | None = strawberry_django.filter_field()


@strawberry_django.filter_type(models.BGPAddressFamily, lookups=True)
class BGPAddressFamilyFilter(PrimaryModelFilter):
    bgprouter: Annotated['BGPRouterFilter', strawberry.lazy('netbox_routing_protocols.graphql.filters')] | None = (
        strawberry_django.filter_field()
    )
    bgprouter_id: ID | None = strawberry_django.filter_field()
    family: BaseFilterLookup[BGPAddressFamilyEnum] | None = strawberry_django.filter_field()
    enable: FilterLookup[bool] | None = strawberry_django.filter_field()
    aggregate_routes: Annotated['PrefixFilter', strawberry.lazy('ipam.graphql.filters')] | None = (
        strawberry_django.filter_field()
    )
    aggregate_route_map: (
        Annotated['RouteMapFilter', strawberry.lazy('netbox_routing_protocols.graphql.filters')] | None
    ) = strawberry_django.filter_field()
    aggregate_route_map_id: ID | None = strawberry_django.filter_field()
    networks: Annotated['PrefixFilter', strawberry.lazy('ipam.graphql.filters')] | None = (
        strawberry_django.filter_field()
    )
    network_route_map: (
        Annotated['RouteMapFilter', strawberry.lazy('netbox_routing_protocols.graphql.filters')] | None
    ) = strawberry_django.filter_field()
    network_route_map_id: ID | None = strawberry_django.filter_field()
    export_to_evpn: FilterLookup[bool] | None = strawberry_django.filter_field()


@strawberry_django.filter_type(models.BGPAddressFamilyRedistribute, lookups=True)
class BGPAddressFamilyRedistributeFilter(PrimaryModelFilter):
    family: Annotated['BGPAddressFamilyFilter', strawberry.lazy('netbox_routing_protocols.graphql.filters')] | None = (
        strawberry_django.filter_field()
    )
    family_id: ID | None = strawberry_django.filter_field()
    protocol: BaseFilterLookup[BGPRedistributeProtocolEnum] | None = strawberry_django.filter_field()
    enable: FilterLookup[bool] | None = strawberry_django.filter_field()
    route_map: Annotated['RouteMapFilter', strawberry.lazy('netbox_routing_protocols.graphql.filters')] | None = (
        strawberry_django.filter_field()
    )
    route_map_id: ID | None = strawberry_django.filter_field()


@dataclass
class BGPSessionAddressFamilyFilterMixin:
    """Per-address-family settings shared by peer and peer-group address families."""

    family: BaseFilterLookup[BGPAddressFamilyEnum] | None = strawberry_django.filter_field()
    enable: FilterLookup[bool] | None = strawberry_django.filter_field()
    inbound_policy: Annotated['RouteMapFilter', strawberry.lazy('netbox_routing_protocols.graphql.filters')] | None = (
        strawberry_django.filter_field()
    )
    inbound_policy_id: ID | None = strawberry_django.filter_field()
    outbound_policy: Annotated['RouteMapFilter', strawberry.lazy('netbox_routing_protocols.graphql.filters')] | None = (
        strawberry_django.filter_field()
    )
    outbound_policy_id: ID | None = strawberry_django.filter_field()
    soft_reconfiguration: FilterLookup[bool] | None = strawberry_django.filter_field()
    default_originate: FilterLookup[bool] | None = strawberry_django.filter_field()
    route_reflector_client: FilterLookup[bool] | None = strawberry_django.filter_field()


@strawberry_django.filter_type(models.BGPPeerAddressFamily, lookups=True)
class BGPPeerAddressFamilyFilter(BGPSessionAddressFamilyFilterMixin, PrimaryModelFilter):
    peer: Annotated['BGPPeerFilter', strawberry.lazy('netbox_routing_protocols.graphql.filters')] | None = (
        strawberry_django.filter_field()
    )
    peer_id: ID | None = strawberry_django.filter_field()


@strawberry_django.filter_type(models.BGPPeergroupAddressFamily, lookups=True)
class BGPPeergroupAddressFamilyFilter(BGPSessionAddressFamilyFilterMixin, PrimaryModelFilter):
    peergroup: Annotated['BGPPeergroupFilter', strawberry.lazy('netbox_routing_protocols.graphql.filters')] | None = (
        strawberry_django.filter_field()
    )
    peergroup_id: ID | None = strawberry_django.filter_field()
