"""
REST API serializers.

Conventions applied consistently across every serializer here:

* ``brief_fields`` lists only fields that are actually declared in ``fields``.
  Nested representations are rendered from ``brief_fields``, so anything listed
  there that does not exist raises at render time.
* Annotated counts (``rule_count``) are declared with a default so that a nested
  instance — which never carries the viewset's queryset annotation — serializes
  cleanly instead of raising. They are deliberately excluded from
  ``brief_fields``.
* ``password`` on BGP peers and peer groups is a BGP MD5 authentication key and
  is write-only: it can be set and updated, but is never returned.
"""

from rest_framework import serializers

from dcim.api.serializers import DeviceSerializer, InterfaceSerializer
from ipam.api.serializers import ASNSerializer, IPAddressSerializer, PrefixSerializer, VRFSerializer
from ipam.models import Prefix
from netbox.api.fields import ChoiceField, SerializedPKRelatedField
from netbox.api.serializers import PrimaryModelSerializer

from netbox_routing_protocols.choices import (
    ActionChoices,
    AddressFamilyChoices,
    BGPAddressFamilyChoices,
    BGPRedistributeProtocolChoices,
)
from netbox_routing_protocols.models import (
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
    'BGPAddressFamilyRedistributeSerializer',
    'BGPAddressFamilySerializer',
    'BGPPeerAddressFamilySerializer',
    'BGPPeerSerializer',
    'BGPPeergroupAddressFamilySerializer',
    'BGPPeergroupSerializer',
    'BGPRouterSerializer',
    'PrefixListRuleSerializer',
    'PrefixListSerializer',
    'RouteMapRuleSerializer',
    'RouteMapSerializer',
    'StaticRouteSerializer',
)

# Every model in this plugin derives from PrimaryModel, so every serializer carries
# the same trailing block of NetBox fields.
PRIMARY_MODEL_FIELDS = (
    'description',
    'comments',
    'owner',
    'tags',
    'custom_fields',
    'created',
    'last_updated',
)


def _detail_view_name(model_name: str) -> str:
    """Return the REST API detail view name for one of this plugin's models."""
    return f'plugins-api:netbox_routing_protocols-api:{model_name}-detail'


#
# Static routing
#


class StaticRouteSerializer(PrimaryModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name=_detail_view_name('staticroute'))
    # Model property, not a column.
    name = serializers.CharField(read_only=True)
    device = DeviceSerializer(nested=True)
    vrf = VRFSerializer(nested=True, required=False, allow_null=True)
    prefix = PrefixSerializer(nested=True, required=False, allow_null=True)
    nexthop = IPAddressSerializer(nested=True)

    class Meta:
        model = StaticRoute
        fields = (
            'id',
            'url',
            'display',
            'name',
            'device',
            'vrf',
            'prefix',
            'nexthop',
            'default_route',
            *PRIMARY_MODEL_FIELDS,
        )
        brief_fields = ('id', 'url', 'display', 'name')


#
# Routing policy
#


class PrefixListSerializer(PrimaryModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name=_detail_view_name('prefixlist'))
    device = DeviceSerializer(nested=True)
    address_family = ChoiceField(choices=AddressFamilyChoices)
    # Populated by an annotation on the viewset's queryset. A nested instance has no
    # such attribute, hence the default; and it is kept out of brief_fields so that
    # nesting a prefix list inside another object never touches it.
    rule_count = serializers.IntegerField(read_only=True, default=None)

    class Meta:
        model = PrefixList
        fields = (
            'id',
            'url',
            'display',
            'name',
            'device',
            'address_family',
            *PRIMARY_MODEL_FIELDS,
            'rule_count',
        )
        brief_fields = ('id', 'url', 'display', 'name')


class PrefixListRuleSerializer(PrimaryModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name=_detail_view_name('prefixlistrule'))
    # Model property, not a column.
    name = serializers.CharField(read_only=True)
    prefix_list = PrefixListSerializer(nested=True)
    action = ChoiceField(choices=ActionChoices)
    prefix = PrefixSerializer(nested=True, required=False, allow_null=True)

    class Meta:
        model = PrefixListRule
        fields = (
            'id',
            'url',
            'display',
            'name',
            'prefix_list',
            'sequence',
            'action',
            'prefix',
            'match_default',
            'match_any',
            'min_prefix_length',
            'max_prefix_length',
            *PRIMARY_MODEL_FIELDS,
        )
        brief_fields = ('id', 'url', 'display', 'name')


class RouteMapSerializer(PrimaryModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name=_detail_view_name('routemap'))
    device = DeviceSerializer(nested=True)
    # See PrefixListSerializer.rule_count.
    rule_count = serializers.IntegerField(read_only=True, default=None)

    class Meta:
        model = RouteMap
        fields = (
            'id',
            'url',
            'display',
            'name',
            'device',
            *PRIMARY_MODEL_FIELDS,
            'rule_count',
        )
        brief_fields = ('id', 'url', 'display', 'name')


class RouteMapRuleSerializer(PrimaryModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name=_detail_view_name('routemaprule'))
    # Model property, not a column.
    name = serializers.CharField(read_only=True)
    route_map = RouteMapSerializer(nested=True)
    action = ChoiceField(choices=ActionChoices)
    prefix_list = PrefixListSerializer(nested=True, required=False, allow_null=True)

    class Meta:
        model = RouteMapRule
        fields = (
            'id',
            'url',
            'display',
            'name',
            'route_map',
            'sequence',
            'action',
            'prefix_list',
            'match_any',
            *PRIMARY_MODEL_FIELDS,
        )
        brief_fields = ('id', 'url', 'display', 'name')


#
# BGP
#


class BGPRouterSerializer(PrimaryModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name=_detail_view_name('bgprouter'))
    # Model property, not a column.
    name = serializers.CharField(read_only=True)
    device = DeviceSerializer(nested=True)
    vrf = VRFSerializer(nested=True)
    asn = ASNSerializer(nested=True, required=False, allow_null=True)
    router_id = IPAddressSerializer(nested=True, required=False, allow_null=True)

    class Meta:
        model = BGPRouter
        fields = (
            'id',
            'url',
            'display',
            'name',
            'device',
            'vrf',
            'enable',
            'asn',
            'router_id',
            'aspath_ignore',
            'route_reflection',
            'enable_evpn',
            *PRIMARY_MODEL_FIELDS,
        )
        brief_fields = ('id', 'url', 'display', 'name')


class BGPPeergroupSerializer(PrimaryModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name=_detail_view_name('bgppeergroup'))
    bgprouter = BGPRouterSerializer(nested=True)
    remote_as = ASNSerializer(nested=True)
    # BGP MD5 authentication key: settable, never returned.
    password = serializers.CharField(
        max_length=255,
        write_only=True,
        required=False,
        allow_blank=True,
    )

    class Meta:
        model = BGPPeergroup
        # device and vrf are properties proxied through bgprouter, not columns.
        fields = (
            'id',
            'url',
            'display',
            'name',
            'bgprouter',
            'enable',
            'remote_as',
            'bfd',
            'password',
            'ebgp_multihop',
            'ebgp_multihop_ttl',
            *PRIMARY_MODEL_FIELDS,
        )
        brief_fields = ('id', 'url', 'display', 'name')


class BGPPeerSerializer(PrimaryModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name=_detail_view_name('bgppeer'))
    # Model property, not a column.
    name = serializers.CharField(read_only=True)
    bgprouter = BGPRouterSerializer(nested=True)
    remote_as = ASNSerializer(nested=True)
    # BGP MD5 authentication key: settable, never returned.
    password = serializers.CharField(
        max_length=255,
        write_only=True,
        required=False,
        allow_blank=True,
    )
    remote_address = IPAddressSerializer(nested=True, required=False, allow_null=True)
    interface = InterfaceSerializer(nested=True, required=False, allow_null=True)
    peergroup = BGPPeergroupSerializer(nested=True, required=False, allow_null=True)

    class Meta:
        model = BGPPeer
        # device and vrf are properties proxied through bgprouter, not columns.
        fields = (
            'id',
            'url',
            'display',
            'name',
            'bgprouter',
            'enable',
            'remote_address',
            'interface',
            'peergroup',
            'remote_as',
            'bfd',
            'password',
            'ebgp_multihop',
            'ebgp_multihop_ttl',
            *PRIMARY_MODEL_FIELDS,
        )
        brief_fields = ('id', 'url', 'display', 'name')


class BGPAddressFamilySerializer(PrimaryModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name=_detail_view_name('bgpaddressfamily'))
    bgprouter = BGPRouterSerializer(nested=True)
    family = ChoiceField(choices=BGPAddressFamilyChoices)
    aggregate_routes = SerializedPKRelatedField(
        queryset=Prefix.objects.all(),
        serializer=PrefixSerializer,
        nested=True,
        required=False,
        many=True,
    )
    aggregate_route_map = RouteMapSerializer(nested=True, required=False, allow_null=True)
    networks = SerializedPKRelatedField(
        queryset=Prefix.objects.all(),
        serializer=PrefixSerializer,
        nested=True,
        required=False,
        many=True,
    )
    network_route_map = RouteMapSerializer(nested=True, required=False, allow_null=True)

    class Meta:
        model = BGPAddressFamily
        # device and vrf are properties proxied through bgprouter, not columns.
        fields = (
            'id',
            'url',
            'display',
            'bgprouter',
            'family',
            'enable',
            'aggregate_routes',
            'aggregate_route_map',
            'networks',
            'network_route_map',
            'export_to_evpn',
            *PRIMARY_MODEL_FIELDS,
        )
        brief_fields = ('id', 'url', 'display', 'family')


class BGPAddressFamilyRedistributeSerializer(PrimaryModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name=_detail_view_name('bgpaddressfamilyredistribute'))
    # Model property, not a column.
    name = serializers.CharField(read_only=True)
    family = BGPAddressFamilySerializer(nested=True)
    protocol = ChoiceField(choices=BGPRedistributeProtocolChoices)
    route_map = RouteMapSerializer(nested=True, required=False, allow_null=True)

    class Meta:
        model = BGPAddressFamilyRedistribute
        fields = (
            'id',
            'url',
            'display',
            'name',
            'family',
            'protocol',
            'enable',
            'route_map',
            *PRIMARY_MODEL_FIELDS,
        )
        brief_fields = ('id', 'url', 'display', 'name')


class BGPPeerAddressFamilySerializer(PrimaryModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name=_detail_view_name('bgppeeraddressfamily'))
    # Model property, not a column.
    name = serializers.CharField(read_only=True)
    peer = BGPPeerSerializer(nested=True)
    family = ChoiceField(choices=BGPAddressFamilyChoices)
    inbound_policy = RouteMapSerializer(nested=True, required=False, allow_null=True)
    outbound_policy = RouteMapSerializer(nested=True, required=False, allow_null=True)

    class Meta:
        model = BGPPeerAddressFamily
        fields = (
            'id',
            'url',
            'display',
            'name',
            'peer',
            'family',
            'enable',
            'inbound_policy',
            'outbound_policy',
            'soft_reconfiguration',
            'default_originate',
            'route_reflector_client',
            *PRIMARY_MODEL_FIELDS,
        )
        brief_fields = ('id', 'url', 'display', 'name')


class BGPPeergroupAddressFamilySerializer(PrimaryModelSerializer):
    url = serializers.HyperlinkedIdentityField(view_name=_detail_view_name('bgppeergroupaddressfamily'))
    # Model property, not a column.
    name = serializers.CharField(read_only=True)
    peergroup = BGPPeergroupSerializer(nested=True)
    family = ChoiceField(choices=BGPAddressFamilyChoices)
    inbound_policy = RouteMapSerializer(nested=True, required=False, allow_null=True)
    outbound_policy = RouteMapSerializer(nested=True, required=False, allow_null=True)

    class Meta:
        model = BGPPeergroupAddressFamily
        fields = (
            'id',
            'url',
            'display',
            'name',
            'peergroup',
            'family',
            'enable',
            'inbound_policy',
            'outbound_policy',
            'soft_reconfiguration',
            'default_originate',
            'route_reflector_client',
            *PRIMARY_MODEL_FIELDS,
        )
        brief_fields = ('id', 'url', 'display', 'name')
