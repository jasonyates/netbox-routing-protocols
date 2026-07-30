"""
REST API viewsets.

Querysets carry the joins and prefetches needed by the fields each serializer
actually renders — including the joins behind the ``name`` properties used as
natural keys in nested representations — plus the ``rule_count`` annotations
that PrefixList and RouteMap expose.
"""

from rest_framework.routers import APIRootView

from netbox.api.viewsets import NetBoxModelViewSet
from utilities.query import count_related

from netbox_routing_protocols.filtersets import (
    BFDProfileFilterSet,
    BGPAddressFamilyFilterSet,
    BGPAddressFamilyRedistributeFilterSet,
    BGPPeerAddressFamilyFilterSet,
    BGPPeerFilterSet,
    BGPPeergroupAddressFamilyFilterSet,
    BGPPeergroupFilterSet,
    BGPRouterFilterSet,
    PrefixListFilterSet,
    PrefixListRuleFilterSet,
    RouteMapFilterSet,
    RouteMapRuleFilterSet,
    StaticRouteFilterSet,
)
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

from . import serializers

__all__ = (
    'BGPAddressFamilyRedistributeViewSet',
    'BGPAddressFamilyViewSet',
    'BGPPeerAddressFamilyViewSet',
    'BGPPeerViewSet',
    'BGPPeergroupAddressFamilyViewSet',
    'BGPPeergroupViewSet',
    'BGPRouterViewSet',
    'PrefixListRuleViewSet',
    'PrefixListViewSet',
    'RouteMapRuleViewSet',
    'RouteMapViewSet',
    'RoutingProtocolsRootView',
    'StaticRouteViewSet',
)


class RoutingProtocolsRootView(APIRootView):
    """Routing Protocols plugin API root view."""

    def get_view_name(self):
        return 'Routing Protocols'


#
# Static routing
#


class StaticRouteViewSet(NetBoxModelViewSet):
    queryset = StaticRoute.objects.select_related(
        'device',
        'vrf',
        'prefix',
        'nexthop',
        'owner',
    ).prefetch_related('tags')
    serializer_class = serializers.StaticRouteSerializer
    filterset_class = StaticRouteFilterSet


#
# Routing policy
#


class PrefixListViewSet(NetBoxModelViewSet):
    queryset = (
        PrefixList.objects.select_related('device', 'owner')
        .prefetch_related('tags')
        .annotate(rule_count=count_related(PrefixListRule, 'prefix_list'))
    )
    serializer_class = serializers.PrefixListSerializer
    filterset_class = PrefixListFilterSet


class PrefixListRuleViewSet(NetBoxModelViewSet):
    queryset = PrefixListRule.objects.select_related(
        'prefix_list',
        'prefix',
        'owner',
    ).prefetch_related('tags')
    serializer_class = serializers.PrefixListRuleSerializer
    filterset_class = PrefixListRuleFilterSet


class RouteMapViewSet(NetBoxModelViewSet):
    queryset = (
        RouteMap.objects.select_related('device', 'owner')
        .prefetch_related('tags')
        .annotate(rule_count=count_related(RouteMapRule, 'route_map'))
    )
    serializer_class = serializers.RouteMapSerializer
    filterset_class = RouteMapFilterSet


class RouteMapRuleViewSet(NetBoxModelViewSet):
    queryset = RouteMapRule.objects.select_related(
        'route_map',
        'prefix_list',
        'owner',
    ).prefetch_related('tags')
    serializer_class = serializers.RouteMapRuleSerializer
    filterset_class = RouteMapRuleFilterSet


#
# BFD
#


class BFDProfileViewSet(NetBoxModelViewSet):
    queryset = BFDProfile.objects.select_related('device', 'owner').prefetch_related('tags')
    serializer_class = serializers.BFDProfileSerializer
    filterset_class = BFDProfileFilterSet


#
# BGP
#


class BGPRouterViewSet(NetBoxModelViewSet):
    queryset = BGPRouter.objects.select_related(
        'device',
        'vrf',
        'asn',
        'router_id',
        'owner',
    ).prefetch_related('tags')
    serializer_class = serializers.BGPRouterSerializer
    filterset_class = BGPRouterFilterSet


class BGPPeergroupViewSet(NetBoxModelViewSet):
    # BGPRouter.name is built from its device and VRF, so both are joined here.
    queryset = BGPPeergroup.objects.select_related(
        'bgprouter',
        'bgprouter__device',
        'bgprouter__vrf',
        'remote_as',
        'bfd',
        'owner',
    ).prefetch_related('tags')
    serializer_class = serializers.BGPPeergroupSerializer
    filterset_class = BGPPeergroupFilterSet


class BGPPeerViewSet(NetBoxModelViewSet):
    queryset = BGPPeer.objects.select_related(
        'bgprouter',
        'bgprouter__device',
        'bgprouter__vrf',
        'remote_as',
        'remote_address',
        'interface',
        'peergroup',
        'bfd',
        'owner',
    ).prefetch_related('tags')
    serializer_class = serializers.BGPPeerSerializer
    filterset_class = BGPPeerFilterSet


class BGPAddressFamilyViewSet(NetBoxModelViewSet):
    queryset = BGPAddressFamily.objects.select_related(
        'bgprouter',
        'bgprouter__device',
        'bgprouter__vrf',
        'aggregate_route_map',
        'network_route_map',
        'owner',
    ).prefetch_related('aggregate_routes', 'networks', 'tags')
    serializer_class = serializers.BGPAddressFamilySerializer
    filterset_class = BGPAddressFamilyFilterSet


class BGPAddressFamilyRedistributeViewSet(NetBoxModelViewSet):
    queryset = BGPAddressFamilyRedistribute.objects.select_related(
        'family',
        'route_map',
        'owner',
    ).prefetch_related('tags')
    serializer_class = serializers.BGPAddressFamilyRedistributeSerializer
    filterset_class = BGPAddressFamilyRedistributeFilterSet


class BGPPeerAddressFamilyViewSet(NetBoxModelViewSet):
    # BGPPeer.name resolves through either its interface or its remote address.
    queryset = BGPPeerAddressFamily.objects.select_related(
        'peer',
        'peer__interface',
        'peer__remote_address',
        'inbound_policy',
        'outbound_policy',
        'owner',
    ).prefetch_related('tags')
    serializer_class = serializers.BGPPeerAddressFamilySerializer
    filterset_class = BGPPeerAddressFamilyFilterSet


class BGPPeergroupAddressFamilyViewSet(NetBoxModelViewSet):
    queryset = BGPPeergroupAddressFamily.objects.select_related(
        'peergroup',
        'inbound_policy',
        'outbound_policy',
        'owner',
    ).prefetch_related('tags')
    serializer_class = serializers.BGPPeergroupAddressFamilySerializer
    filterset_class = BGPPeergroupAddressFamilyFilterSet
