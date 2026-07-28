import re

import django_filters
from django.db.models import Q
from django.utils.translation import gettext as _

from dcim.models import Device, Interface
from ipam.models import ASN, VRF, IPAddress, Prefix
from netbox.filtersets import PrimaryModelFilterSet
from utilities.filtersets import register_filterset

from netbox_routing_protocols.choices import BGPAddressFamilyChoices, BGPRedistributeProtocolChoices
from netbox_routing_protocols.models import (
    BGPAddressFamily,
    BGPAddressFamilyRedistribute,
    BGPPeer,
    BGPPeerAddressFamily,
    BGPPeergroup,
    BGPPeergroupAddressFamily,
    BGPRouter,
    RouteMap,
)

__all__ = (
    'BGPAddressFamilyFilterSet',
    'BGPAddressFamilyRedistributeFilterSet',
    'BGPPeerAddressFamilyFilterSet',
    'BGPPeerFilterSet',
    'BGPPeergroupAddressFamilyFilterSet',
    'BGPPeergroupFilterSet',
    'BGPRouterFilterSet',
)

# Free text is only matched against IPAM columns when it could plausibly be part of an address.
# `istartswith` is safe on NetBox's CIDR fields (it casts the column to TEXT); `contains` is *not* —
# there it means network containment and raises on non-CIDR input.
IP_LIKE = re.compile(r'^[0-9a-fA-F.:/]+$')


@register_filterset
class BGPRouterFilterSet(PrimaryModelFilterSet):
    device_id = django_filters.ModelMultipleChoiceFilter(
        field_name='device',
        queryset=Device.objects.all(),
        label=_('Device (ID)'),
    )
    device = django_filters.ModelMultipleChoiceFilter(
        field_name='device__name',
        queryset=Device.objects.all(),
        to_field_name='name',
        label=_('Device (name)'),
    )
    vrf_id = django_filters.ModelMultipleChoiceFilter(
        field_name='vrf',
        queryset=VRF.objects.all(),
        label=_('VRF (ID)'),
    )
    vrf = django_filters.ModelMultipleChoiceFilter(
        field_name='vrf__name',
        queryset=VRF.objects.all(),
        to_field_name='name',
        label=_('VRF (name)'),
    )
    asn_id = django_filters.ModelMultipleChoiceFilter(
        field_name='asn',
        queryset=ASN.objects.all(),
        label=_('ASN (ID)'),
    )
    asn = django_filters.ModelMultipleChoiceFilter(
        field_name='asn__asn',
        queryset=ASN.objects.all(),
        to_field_name='asn',
        label=_('ASN (number)'),
    )
    router_id_id = django_filters.ModelMultipleChoiceFilter(
        field_name='router_id',
        queryset=IPAddress.objects.all(),
        label=_('Router ID (ID)'),
    )

    class Meta:
        model = BGPRouter
        fields = (
            'id',
            'enable',
            'aspath_ignore',
            'route_reflection',
            'enable_evpn',
            'description',
        )

    def search(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset

        query = (
            Q(device__name__icontains=value)
            | Q(vrf__name__icontains=value)
            | Q(description__icontains=value)
            | Q(comments__icontains=value)
        )
        if value.isdigit():
            query |= Q(asn__asn=int(value))
        if IP_LIKE.match(value):
            query |= Q(router_id__address__istartswith=value)

        return queryset.filter(query)


@register_filterset
class BGPPeergroupFilterSet(PrimaryModelFilterSet):
    bgprouter_id = django_filters.ModelMultipleChoiceFilter(
        field_name='bgprouter',
        queryset=BGPRouter.objects.all(),
        label=_('BGP router (ID)'),
    )
    device_id = django_filters.ModelMultipleChoiceFilter(
        field_name='bgprouter__device',
        queryset=Device.objects.all(),
        label=_('Device (ID)'),
    )
    device = django_filters.ModelMultipleChoiceFilter(
        field_name='bgprouter__device__name',
        queryset=Device.objects.all(),
        to_field_name='name',
        label=_('Device (name)'),
    )
    vrf_id = django_filters.ModelMultipleChoiceFilter(
        field_name='bgprouter__vrf',
        queryset=VRF.objects.all(),
        label=_('VRF (ID)'),
    )
    remote_as_id = django_filters.ModelMultipleChoiceFilter(
        field_name='remote_as',
        queryset=ASN.objects.all(),
        label=_('Remote AS (ID)'),
    )
    remote_as = django_filters.ModelMultipleChoiceFilter(
        field_name='remote_as__asn',
        queryset=ASN.objects.all(),
        to_field_name='asn',
        label=_('Remote AS (number)'),
    )

    class Meta:
        model = BGPPeergroup
        fields = (
            'id',
            'name',
            'enable',
            'bfd',
            'ebgp_multihop',
            'ebgp_multihop_ttl',
            'description',
        )

    def search(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset

        query = (
            Q(name__icontains=value)
            | Q(bgprouter__device__name__icontains=value)
            | Q(bgprouter__vrf__name__icontains=value)
            | Q(description__icontains=value)
            | Q(comments__icontains=value)
        )
        if value.isdigit():
            query |= Q(remote_as__asn=int(value))

        return queryset.filter(query)


@register_filterset
class BGPPeerFilterSet(PrimaryModelFilterSet):
    bgprouter_id = django_filters.ModelMultipleChoiceFilter(
        field_name='bgprouter',
        queryset=BGPRouter.objects.all(),
        label=_('BGP router (ID)'),
    )
    device_id = django_filters.ModelMultipleChoiceFilter(
        field_name='bgprouter__device',
        queryset=Device.objects.all(),
        label=_('Device (ID)'),
    )
    device = django_filters.ModelMultipleChoiceFilter(
        field_name='bgprouter__device__name',
        queryset=Device.objects.all(),
        to_field_name='name',
        label=_('Device (name)'),
    )
    vrf_id = django_filters.ModelMultipleChoiceFilter(
        field_name='bgprouter__vrf',
        queryset=VRF.objects.all(),
        label=_('VRF (ID)'),
    )
    peergroup_id = django_filters.ModelMultipleChoiceFilter(
        field_name='peergroup',
        queryset=BGPPeergroup.objects.all(),
        label=_('Peer group (ID)'),
    )
    peergroup = django_filters.ModelMultipleChoiceFilter(
        field_name='peergroup__name',
        queryset=BGPPeergroup.objects.all(),
        to_field_name='name',
        label=_('Peer group (name)'),
    )
    remote_address_id = django_filters.ModelMultipleChoiceFilter(
        field_name='remote_address',
        queryset=IPAddress.objects.all(),
        label=_('Remote address (ID)'),
    )
    interface_id = django_filters.ModelMultipleChoiceFilter(
        field_name='interface',
        queryset=Interface.objects.all(),
        label=_('Interface (ID)'),
    )
    remote_as_id = django_filters.ModelMultipleChoiceFilter(
        field_name='remote_as',
        queryset=ASN.objects.all(),
        label=_('Remote AS (ID)'),
    )
    remote_as = django_filters.ModelMultipleChoiceFilter(
        field_name='remote_as__asn',
        queryset=ASN.objects.all(),
        to_field_name='asn',
        label=_('Remote AS (number)'),
    )

    class Meta:
        model = BGPPeer
        fields = (
            'id',
            'enable',
            'bfd',
            'ebgp_multihop',
            'ebgp_multihop_ttl',
            'description',
        )

    def search(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset

        query = (
            Q(bgprouter__device__name__icontains=value)
            | Q(bgprouter__vrf__name__icontains=value)
            | Q(peergroup__name__icontains=value)
            | Q(interface__name__icontains=value)
            | Q(description__icontains=value)
            | Q(comments__icontains=value)
        )
        if value.isdigit():
            query |= Q(remote_as__asn=int(value))
        if IP_LIKE.match(value):
            query |= Q(remote_address__address__istartswith=value)

        return queryset.filter(query)


@register_filterset
class BGPAddressFamilyFilterSet(PrimaryModelFilterSet):
    bgprouter_id = django_filters.ModelMultipleChoiceFilter(
        field_name='bgprouter',
        queryset=BGPRouter.objects.all(),
        label=_('BGP router (ID)'),
    )
    device_id = django_filters.ModelMultipleChoiceFilter(
        field_name='bgprouter__device',
        queryset=Device.objects.all(),
        label=_('Device (ID)'),
    )
    device = django_filters.ModelMultipleChoiceFilter(
        field_name='bgprouter__device__name',
        queryset=Device.objects.all(),
        to_field_name='name',
        label=_('Device (name)'),
    )
    vrf_id = django_filters.ModelMultipleChoiceFilter(
        field_name='bgprouter__vrf',
        queryset=VRF.objects.all(),
        label=_('VRF (ID)'),
    )
    aggregate_route_map_id = django_filters.ModelMultipleChoiceFilter(
        field_name='aggregate_route_map',
        queryset=RouteMap.objects.all(),
        label=_('Aggregate route map (ID)'),
    )
    network_route_map_id = django_filters.ModelMultipleChoiceFilter(
        field_name='network_route_map',
        queryset=RouteMap.objects.all(),
        label=_('Network route map (ID)'),
    )
    # `aggregate_routes` and `networks` are both many-to-many to ipam.Prefix, so they
    # cannot both be called `prefix_id`. Each gets a singular name of its own, by ID
    # and by prefix value, so "which address families advertise this prefix?" is
    # answerable from either side. `distinct` is required: joining a multi-valued
    # relation would otherwise repeat a row once per matching prefix.
    aggregate_route_id = django_filters.ModelMultipleChoiceFilter(
        field_name='aggregate_routes',
        queryset=Prefix.objects.all(),
        distinct=True,
        label=_('Aggregate route (ID)'),
    )
    aggregate_route = django_filters.ModelMultipleChoiceFilter(
        field_name='aggregate_routes__prefix',
        queryset=Prefix.objects.all(),
        to_field_name='prefix',
        distinct=True,
        label=_('Aggregate route (prefix)'),
    )
    network_id = django_filters.ModelMultipleChoiceFilter(
        field_name='networks',
        queryset=Prefix.objects.all(),
        distinct=True,
        label=_('Network (ID)'),
    )
    network = django_filters.ModelMultipleChoiceFilter(
        field_name='networks__prefix',
        queryset=Prefix.objects.all(),
        to_field_name='prefix',
        distinct=True,
        label=_('Network (prefix)'),
    )
    family = django_filters.MultipleChoiceFilter(
        choices=BGPAddressFamilyChoices,
        label=_('Address family'),
    )

    class Meta:
        model = BGPAddressFamily
        fields = ('id', 'enable', 'export_to_evpn', 'description')

    def search(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset

        return queryset.filter(
            Q(bgprouter__device__name__icontains=value)
            | Q(bgprouter__vrf__name__icontains=value)
            | Q(aggregate_route_map__name__icontains=value)
            | Q(network_route_map__name__icontains=value)
            | Q(description__icontains=value)
            | Q(comments__icontains=value)
        )


@register_filterset
class BGPAddressFamilyRedistributeFilterSet(PrimaryModelFilterSet):
    family_id = django_filters.ModelMultipleChoiceFilter(
        field_name='family',
        queryset=BGPAddressFamily.objects.all(),
        label=_('Address family (ID)'),
    )
    bgprouter_id = django_filters.ModelMultipleChoiceFilter(
        field_name='family__bgprouter',
        queryset=BGPRouter.objects.all(),
        label=_('BGP router (ID)'),
    )
    device_id = django_filters.ModelMultipleChoiceFilter(
        field_name='family__bgprouter__device',
        queryset=Device.objects.all(),
        label=_('Device (ID)'),
    )
    device = django_filters.ModelMultipleChoiceFilter(
        field_name='family__bgprouter__device__name',
        queryset=Device.objects.all(),
        to_field_name='name',
        label=_('Device (name)'),
    )
    route_map_id = django_filters.ModelMultipleChoiceFilter(
        field_name='route_map',
        queryset=RouteMap.objects.all(),
        label=_('Route map (ID)'),
    )
    protocol = django_filters.MultipleChoiceFilter(
        choices=BGPRedistributeProtocolChoices,
        label=_('Protocol'),
    )

    class Meta:
        model = BGPAddressFamilyRedistribute
        fields = ('id', 'enable', 'description')

    def search(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset

        return queryset.filter(
            Q(family__bgprouter__device__name__icontains=value)
            | Q(family__bgprouter__vrf__name__icontains=value)
            | Q(route_map__name__icontains=value)
            | Q(description__icontains=value)
            | Q(comments__icontains=value)
        )


@register_filterset
class BGPPeerAddressFamilyFilterSet(PrimaryModelFilterSet):
    peer_id = django_filters.ModelMultipleChoiceFilter(
        field_name='peer',
        queryset=BGPPeer.objects.all(),
        label=_('BGP peer (ID)'),
    )
    bgprouter_id = django_filters.ModelMultipleChoiceFilter(
        field_name='peer__bgprouter',
        queryset=BGPRouter.objects.all(),
        label=_('BGP router (ID)'),
    )
    device_id = django_filters.ModelMultipleChoiceFilter(
        field_name='peer__bgprouter__device',
        queryset=Device.objects.all(),
        label=_('Device (ID)'),
    )
    device = django_filters.ModelMultipleChoiceFilter(
        field_name='peer__bgprouter__device__name',
        queryset=Device.objects.all(),
        to_field_name='name',
        label=_('Device (name)'),
    )
    vrf_id = django_filters.ModelMultipleChoiceFilter(
        field_name='peer__bgprouter__vrf',
        queryset=VRF.objects.all(),
        label=_('VRF (ID)'),
    )
    inbound_policy_id = django_filters.ModelMultipleChoiceFilter(
        field_name='inbound_policy',
        queryset=RouteMap.objects.all(),
        label=_('Inbound policy (ID)'),
    )
    outbound_policy_id = django_filters.ModelMultipleChoiceFilter(
        field_name='outbound_policy',
        queryset=RouteMap.objects.all(),
        label=_('Outbound policy (ID)'),
    )
    family = django_filters.MultipleChoiceFilter(
        choices=BGPAddressFamilyChoices,
        label=_('Address family'),
    )

    class Meta:
        model = BGPPeerAddressFamily
        fields = (
            'id',
            'enable',
            'soft_reconfiguration',
            'default_originate',
            'route_reflector_client',
            'description',
        )

    def search(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset

        query = (
            Q(peer__bgprouter__device__name__icontains=value)
            | Q(peer__bgprouter__vrf__name__icontains=value)
            | Q(peer__interface__name__icontains=value)
            | Q(inbound_policy__name__icontains=value)
            | Q(outbound_policy__name__icontains=value)
            | Q(description__icontains=value)
            | Q(comments__icontains=value)
        )
        if IP_LIKE.match(value):
            query |= Q(peer__remote_address__address__istartswith=value)

        return queryset.filter(query)


@register_filterset
class BGPPeergroupAddressFamilyFilterSet(PrimaryModelFilterSet):
    peergroup_id = django_filters.ModelMultipleChoiceFilter(
        field_name='peergroup',
        queryset=BGPPeergroup.objects.all(),
        label=_('BGP peer group (ID)'),
    )
    peergroup = django_filters.ModelMultipleChoiceFilter(
        field_name='peergroup__name',
        queryset=BGPPeergroup.objects.all(),
        to_field_name='name',
        label=_('BGP peer group (name)'),
    )
    bgprouter_id = django_filters.ModelMultipleChoiceFilter(
        field_name='peergroup__bgprouter',
        queryset=BGPRouter.objects.all(),
        label=_('BGP router (ID)'),
    )
    device_id = django_filters.ModelMultipleChoiceFilter(
        field_name='peergroup__bgprouter__device',
        queryset=Device.objects.all(),
        label=_('Device (ID)'),
    )
    device = django_filters.ModelMultipleChoiceFilter(
        field_name='peergroup__bgprouter__device__name',
        queryset=Device.objects.all(),
        to_field_name='name',
        label=_('Device (name)'),
    )
    vrf_id = django_filters.ModelMultipleChoiceFilter(
        field_name='peergroup__bgprouter__vrf',
        queryset=VRF.objects.all(),
        label=_('VRF (ID)'),
    )
    inbound_policy_id = django_filters.ModelMultipleChoiceFilter(
        field_name='inbound_policy',
        queryset=RouteMap.objects.all(),
        label=_('Inbound policy (ID)'),
    )
    outbound_policy_id = django_filters.ModelMultipleChoiceFilter(
        field_name='outbound_policy',
        queryset=RouteMap.objects.all(),
        label=_('Outbound policy (ID)'),
    )
    family = django_filters.MultipleChoiceFilter(
        choices=BGPAddressFamilyChoices,
        label=_('Address family'),
    )

    class Meta:
        model = BGPPeergroupAddressFamily
        fields = (
            'id',
            'enable',
            'soft_reconfiguration',
            'default_originate',
            'route_reflector_client',
            'description',
        )

    def search(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset

        return queryset.filter(
            Q(peergroup__name__icontains=value)
            | Q(peergroup__bgprouter__device__name__icontains=value)
            | Q(peergroup__bgprouter__vrf__name__icontains=value)
            | Q(inbound_policy__name__icontains=value)
            | Q(outbound_policy__name__icontains=value)
            | Q(description__icontains=value)
            | Q(comments__icontains=value)
        )
