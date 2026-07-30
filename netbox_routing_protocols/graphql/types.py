"""
Strawberry object types for the GraphQL API.

Every model here derives from ``PrimaryModel``, so every type derives from
``NetBoxObjectType`` (change logging, custom fields, journal entries and tags)
plus ``OwnerMixin``, and exposes ``description``/``comments``. Without the
explicit ``OwnerMixin``, the ``owner`` foreign key that ``PrimaryModel``
contributes is auto-generated as the opaque ``DjangoModelType`` (``pk`` only)
rather than ``OwnerType``.

Foreign keys are annotated explicitly with lazy references rather than left to
``fields='__all__'`` auto-resolution, which keeps the cross-app types resolvable
regardless of the order in which app schemas are loaded.
"""

from typing import TYPE_CHECKING, Annotated

import strawberry
import strawberry_django

from netbox.graphql.types import NetBoxObjectType
from users.graphql.mixins import OwnerMixin

from netbox_routing_protocols import models

from .filters import (
    BFDProfileFilter,
    BGPAddressFamilyFilter,
    BGPAddressFamilyRedistributeFilter,
    BGPCommunityFilter,
    BGPCommunityListFilter,
    BGPCommunityListRuleFilter,
    BGPPeerAddressFamilyFilter,
    BGPPeerFilter,
    BGPPeergroupAddressFamilyFilter,
    BGPPeergroupFilter,
    BGPRouterFilter,
    PrefixListFilter,
    PrefixListRuleFilter,
    RouteMapFilter,
    RouteMapRuleFilter,
    StaticRouteFilter,
)

if TYPE_CHECKING:
    from dcim.graphql.types import DeviceType, InterfaceType
    from ipam.graphql.types import ASNType, IPAddressType, PrefixType, VRFType

__all__ = (
    'BFDProfileType',
    'BGPAddressFamilyRedistributeType',
    'BGPAddressFamilyType',
    'BGPCommunityListRuleType',
    'BGPCommunityListType',
    'BGPCommunityType',
    'BGPPeerAddressFamilyType',
    'BGPPeerType',
    'BGPPeergroupAddressFamilyType',
    'BGPPeergroupType',
    'BGPRouterType',
    'PrefixListRuleType',
    'PrefixListType',
    'RouteMapRuleType',
    'RouteMapType',
    'StaticRouteType',
)


#
# Static routing
#


@strawberry_django.type(
    models.StaticRoute,
    fields='__all__',
    filters=StaticRouteFilter,
    pagination=True,
)
class StaticRouteType(OwnerMixin, NetBoxObjectType):
    device: Annotated['DeviceType', strawberry.lazy('dcim.graphql.types')]
    vrf: Annotated['VRFType', strawberry.lazy('ipam.graphql.types')] | None
    prefix: Annotated['PrefixType', strawberry.lazy('ipam.graphql.types')] | None
    nexthop: Annotated['IPAddressType', strawberry.lazy('ipam.graphql.types')]

    @strawberry_django.field
    def name(self) -> str:
        # StaticRoute.name is a Python property: '0.0.0.0/0' or '::/0' for a
        # default route, otherwise the destination prefix.
        return self.name


#
# Routing policy
#


@strawberry_django.type(
    models.PrefixList,
    fields='__all__',
    filters=PrefixListFilter,
    pagination=True,
)
class PrefixListType(OwnerMixin, NetBoxObjectType):
    device: Annotated['DeviceType', strawberry.lazy('dcim.graphql.types')] | None

    rules: list[Annotated['PrefixListRuleType', strawberry.lazy('netbox_routing_protocols.graphql.types')]]
    route_map_rules: list[Annotated['RouteMapRuleType', strawberry.lazy('netbox_routing_protocols.graphql.types')]]


@strawberry_django.type(
    models.PrefixListRule,
    fields='__all__',
    filters=PrefixListRuleFilter,
    pagination=True,
)
class PrefixListRuleType(OwnerMixin, NetBoxObjectType):
    prefix_list: Annotated['PrefixListType', strawberry.lazy('netbox_routing_protocols.graphql.types')]
    prefix: Annotated['PrefixType', strawberry.lazy('ipam.graphql.types')] | None

    @strawberry_django.field
    def name(self) -> str:
        return self.name


@strawberry_django.type(
    models.RouteMap,
    fields='__all__',
    filters=RouteMapFilter,
    pagination=True,
)
class RouteMapType(OwnerMixin, NetBoxObjectType):
    device: Annotated['DeviceType', strawberry.lazy('dcim.graphql.types')] | None

    rules: list[Annotated['RouteMapRuleType', strawberry.lazy('netbox_routing_protocols.graphql.types')]]


@strawberry_django.type(
    models.RouteMapRule,
    fields='__all__',
    filters=RouteMapRuleFilter,
    pagination=True,
)
class RouteMapRuleType(OwnerMixin, NetBoxObjectType):
    route_map: Annotated['RouteMapType', strawberry.lazy('netbox_routing_protocols.graphql.types')]
    prefix_list: Annotated['PrefixListType', strawberry.lazy('netbox_routing_protocols.graphql.types')] | None

    @strawberry_django.field
    def name(self) -> str:
        return self.name


#
# BGP communities
#


@strawberry_django.type(
    models.BGPCommunity,
    fields='__all__',
    filters=BGPCommunityFilter,
    pagination=True,
)
class BGPCommunityType(OwnerMixin, NetBoxObjectType):
    community_list_rules: list[
        Annotated['BGPCommunityListRuleType', strawberry.lazy('netbox_routing_protocols.graphql.types')]
    ]


@strawberry_django.type(
    models.BGPCommunityList,
    fields='__all__',
    filters=BGPCommunityListFilter,
    pagination=True,
)
class BGPCommunityListType(OwnerMixin, NetBoxObjectType):
    device: Annotated['DeviceType', strawberry.lazy('dcim.graphql.types')] | None

    rules: list[Annotated['BGPCommunityListRuleType', strawberry.lazy('netbox_routing_protocols.graphql.types')]]


@strawberry_django.type(
    models.BGPCommunityListRule,
    fields='__all__',
    filters=BGPCommunityListRuleFilter,
    pagination=True,
)
class BGPCommunityListRuleType(OwnerMixin, NetBoxObjectType):
    community_list: Annotated['BGPCommunityListType', strawberry.lazy('netbox_routing_protocols.graphql.types')]
    community: Annotated['BGPCommunityType', strawberry.lazy('netbox_routing_protocols.graphql.types')]

    @strawberry_django.field
    def name(self) -> str:
        return self.name


#
# BFD
#


@strawberry_django.type(
    models.BFDProfile,
    fields='__all__',
    filters=BFDProfileFilter,
    pagination=True,
)
class BFDProfileType(OwnerMixin, NetBoxObjectType):
    device: Annotated['DeviceType', strawberry.lazy('dcim.graphql.types')] | None

    bgppeers: list[Annotated['BGPPeerType', strawberry.lazy('netbox_routing_protocols.graphql.types')]]
    bgppeergroups: list[Annotated['BGPPeergroupType', strawberry.lazy('netbox_routing_protocols.graphql.types')]]


#
# BGP
#


@strawberry_django.type(
    models.BGPRouter,
    fields='__all__',
    filters=BGPRouterFilter,
    pagination=True,
)
class BGPRouterType(OwnerMixin, NetBoxObjectType):
    device: Annotated['DeviceType', strawberry.lazy('dcim.graphql.types')]
    vrf: Annotated['VRFType', strawberry.lazy('ipam.graphql.types')]
    asn: Annotated['ASNType', strawberry.lazy('ipam.graphql.types')] | None
    router_id: Annotated['IPAddressType', strawberry.lazy('ipam.graphql.types')] | None

    address_families: list[Annotated['BGPAddressFamilyType', strawberry.lazy('netbox_routing_protocols.graphql.types')]]
    bgppeers: list[Annotated['BGPPeerType', strawberry.lazy('netbox_routing_protocols.graphql.types')]]
    bgppeergroups: list[Annotated['BGPPeergroupType', strawberry.lazy('netbox_routing_protocols.graphql.types')]]


@strawberry.type
class BGPPeerAttributesMixin:
    """
    Session attributes shared by BGPPeer and BGPPeergroup.

    ``device`` and ``vrf`` are Python properties fed by ``bgprouter``, so they
    are resolved here rather than being auto-generated from a column. Like every
    resolver-returned relation in NetBox core they are declared optional: a
    non-optional relation makes the generic query builder emit a bare field name
    instead of a subfield selection, which the schema then rejects.
    """

    bgprouter: Annotated['BGPRouterType', strawberry.lazy('netbox_routing_protocols.graphql.types')]
    remote_as: Annotated['ASNType', strawberry.lazy('ipam.graphql.types')]
    bfd: Annotated['BFDProfileType', strawberry.lazy('netbox_routing_protocols.graphql.types')] | None

    @strawberry_django.field(select_related=['bgprouter__device'])
    def device(self) -> Annotated['DeviceType', strawberry.lazy('dcim.graphql.types')] | None:
        return self.device

    @strawberry_django.field(select_related=['bgprouter__vrf'])
    def vrf(self) -> Annotated['VRFType', strawberry.lazy('ipam.graphql.types')] | None:
        return self.vrf


@strawberry_django.type(
    models.BGPPeergroup,
    # `password` (the BGP MD5 key) is included: automation reads it from here to render
    # device configuration. It is returned in plaintext, as it is over REST.
    fields='__all__',
    filters=BGPPeergroupFilter,
    pagination=True,
)
class BGPPeergroupType(BGPPeerAttributesMixin, OwnerMixin, NetBoxObjectType):
    address_families: list[
        Annotated['BGPPeergroupAddressFamilyType', strawberry.lazy('netbox_routing_protocols.graphql.types')]
    ]
    peers: list[Annotated['BGPPeerType', strawberry.lazy('netbox_routing_protocols.graphql.types')]]


@strawberry_django.type(
    models.BGPPeer,
    fields='__all__',
    filters=BGPPeerFilter,
    pagination=True,
)
class BGPPeerType(BGPPeerAttributesMixin, OwnerMixin, NetBoxObjectType):
    remote_address: Annotated['IPAddressType', strawberry.lazy('ipam.graphql.types')] | None
    interface: Annotated['InterfaceType', strawberry.lazy('dcim.graphql.types')] | None
    peergroup: Annotated['BGPPeergroupType', strawberry.lazy('netbox_routing_protocols.graphql.types')] | None

    address_families: list[
        Annotated['BGPPeerAddressFamilyType', strawberry.lazy('netbox_routing_protocols.graphql.types')]
    ]

    @strawberry_django.field
    def name(self) -> str:
        # BGPPeer.name is a Python property: the interface name for an
        # unnumbered session, otherwise the remote address.
        return self.name


@strawberry_django.type(
    models.BGPAddressFamily,
    fields='__all__',
    filters=BGPAddressFamilyFilter,
    pagination=True,
)
class BGPAddressFamilyType(OwnerMixin, NetBoxObjectType):
    bgprouter: Annotated['BGPRouterType', strawberry.lazy('netbox_routing_protocols.graphql.types')]
    aggregate_route_map: Annotated['RouteMapType', strawberry.lazy('netbox_routing_protocols.graphql.types')] | None
    network_route_map: Annotated['RouteMapType', strawberry.lazy('netbox_routing_protocols.graphql.types')] | None

    aggregate_routes: list[Annotated['PrefixType', strawberry.lazy('ipam.graphql.types')]]
    networks: list[Annotated['PrefixType', strawberry.lazy('ipam.graphql.types')]]
    redistributions: list[
        Annotated['BGPAddressFamilyRedistributeType', strawberry.lazy('netbox_routing_protocols.graphql.types')]
    ]

    # Resolver-returned relations are declared optional, matching NetBox core.
    @strawberry_django.field(select_related=['bgprouter__device'])
    def device(self) -> Annotated['DeviceType', strawberry.lazy('dcim.graphql.types')] | None:
        return self.device

    @strawberry_django.field(select_related=['bgprouter__vrf'])
    def vrf(self) -> Annotated['VRFType', strawberry.lazy('ipam.graphql.types')] | None:
        return self.vrf


@strawberry_django.type(
    models.BGPAddressFamilyRedistribute,
    fields='__all__',
    filters=BGPAddressFamilyRedistributeFilter,
    pagination=True,
)
class BGPAddressFamilyRedistributeType(OwnerMixin, NetBoxObjectType):
    family: Annotated['BGPAddressFamilyType', strawberry.lazy('netbox_routing_protocols.graphql.types')]
    route_map: Annotated['RouteMapType', strawberry.lazy('netbox_routing_protocols.graphql.types')] | None


@strawberry.type
class BGPSessionAddressFamilyMixin:
    """Per-address-family settings shared by peer and peer-group address families."""

    inbound_policy: Annotated['RouteMapType', strawberry.lazy('netbox_routing_protocols.graphql.types')] | None
    outbound_policy: Annotated['RouteMapType', strawberry.lazy('netbox_routing_protocols.graphql.types')] | None


@strawberry_django.type(
    models.BGPPeerAddressFamily,
    fields='__all__',
    filters=BGPPeerAddressFamilyFilter,
    pagination=True,
)
class BGPPeerAddressFamilyType(BGPSessionAddressFamilyMixin, OwnerMixin, NetBoxObjectType):
    peer: Annotated['BGPPeerType', strawberry.lazy('netbox_routing_protocols.graphql.types')]


@strawberry_django.type(
    models.BGPPeergroupAddressFamily,
    fields='__all__',
    filters=BGPPeergroupAddressFamilyFilter,
    pagination=True,
)
class BGPPeergroupAddressFamilyType(BGPSessionAddressFamilyMixin, OwnerMixin, NetBoxObjectType):
    peergroup: Annotated['BGPPeergroupType', strawberry.lazy('netbox_routing_protocols.graphql.types')]
