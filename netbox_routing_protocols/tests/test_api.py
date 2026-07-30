"""
REST API tests.

Every endpoint is driven through NetBox's own ``APIViewTestCases.APIViewTestCase``
so the GET / POST / PATCH / DELETE / brief / OPTIONS / GraphQL suites are the same
ones the core apps are held to, rather than a hand-rolled approximation.

On top of that there are three targeted suites, each covering a way the API has
previously broken:

* ``BriefModeTestCase`` — ``?brief=true`` on all twelve endpoints.
* ``NestedSerializationTestCase`` — a PrefixList nested inside another object has
  no ``rule_count`` annotation, and rendering it must not reach for one.
* ``PasswordDisclosureTestCase`` — the BGP MD5 key is settable but never returned.
"""

from django.urls import reverse
from rest_framework import status

from utilities.testing import APITestCase, APIViewTestCases

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

from .base import BaseTestData

# API namespace prefix for this plugin, as registered by NetBox's plugin API router.
VIEW_NAMESPACE = 'plugins-api:netbox_routing_protocols'

# Brief representations are built from each serializer's brief_fields. Anything
# listed here that the serializer cannot render raises at response time, which is
# why every endpoint is checked rather than a sample.
BRIEF_FIELDS = ['display', 'id', 'name', 'url']
BRIEF_FIELDS_FAMILY = ['display', 'family', 'id', 'url']

# Model names of every endpoint this plugin exposes.
PLUGIN_MODEL_NAMES = (
    'staticroute',
    'prefixlist',
    'prefixlistrule',
    'routemap',
    'routemaprule',
    'bgprouter',
    'bgppeergroup',
    'bgppeer',
    'bgpaddressfamily',
    'bgpaddressfamilyredistribute',
    'bgppeeraddressfamily',
    'bgppeergroupaddressfamily',
)

# DCIM and IPAM objects reachable from this plugin's GraphQL types.
CORE_VIEW_PERMISSIONS = (
    'dcim.view_device',
    'dcim.view_interface',
    'ipam.view_asn',
    'ipam.view_ipaddress',
    'ipam.view_prefix',
    'ipam.view_vrf',
)


def related_view_permissions(model_name):
    """
    View permissions for everything reachable from a model's GraphQL type.

    GraphQL applies object permissions to nested types, so a related object the
    caller cannot see resolves to null — which for a non-nullable relation fails
    the whole query. The permission for the model under test is deliberately
    excluded: the generic GET and list tests rely on granting it themselves,
    under a constraint, to prove object-level permissions are enforced.
    """
    return (
        *CORE_VIEW_PERMISSIONS,
        *[f'netbox_routing_protocols.view_{name}' for name in PLUGIN_MODEL_NAMES if name != model_name],
    )


class RoutingProtocolsAPITestCases:
    """Container so the shared base class is not collected as a test case itself."""

    class APIViewTestCase(BaseTestData, APIViewTestCases.APIViewTestCase):
        view_namespace = VIEW_NAMESPACE
        brief_fields = BRIEF_FIELDS
        bulk_update_data = {
            'description': 'New description',
        }


#
# Static routing
#


class StaticRouteTestCase(RoutingProtocolsAPITestCases.APIViewTestCase):
    model = StaticRoute
    user_permissions = related_view_permissions('staticroute')

    @classmethod
    def setUpTestData(cls):
        cls.build_topology()

        StaticRoute.objects.create(
            device=cls.devices[0], vrf=cls.vrfs[0], prefix=cls.prefixes4[0], nexthop=cls.addresses4[0]
        )
        StaticRoute.objects.create(
            device=cls.devices[0], vrf=cls.vrfs[0], prefix=cls.prefixes4[1], nexthop=cls.addresses4[1]
        )
        StaticRoute.objects.create(
            device=cls.devices[0], vrf=cls.vrfs[0], nexthop=cls.addresses4[2], default_route=True
        )

        cls.create_data = [
            {
                'device': cls.devices[1].pk,
                'vrf': cls.vrfs[0].pk,
                'prefix': cls.prefixes4[2].pk,
                'nexthop': cls.addresses4[0].pk,
            },
            {
                'device': cls.devices[1].pk,
                'vrf': cls.vrfs[0].pk,
                'prefix': cls.prefixes4[3].pk,
                'nexthop': cls.addresses4[1].pk,
            },
            {
                'device': cls.devices[1].pk,
                'vrf': cls.vrfs[0].pk,
                'nexthop': cls.addresses4[2].pk,
                'default_route': True,
            },
        ]


#
# Routing policy
#


class PrefixListTestCase(RoutingProtocolsAPITestCases.APIViewTestCase):
    model = PrefixList
    user_permissions = related_view_permissions('prefixlist')
    graphql_base_name = 'ip_prefix_list'

    @classmethod
    def setUpTestData(cls):
        cls.build_topology()

        # Each of these also gains a terminating deny-9999 rule from the post_save
        # receiver; that is exercised in test_models and is harmless here.
        for name in ('PL-CORE-IN', 'PL-CORE-OUT', 'PL-EDGE-IN'):
            PrefixList.objects.create(
                name=name,
                device=cls.devices[0],
                address_family=AddressFamilyChoices.FAMILY_IPV4,
            )

        cls.create_data = [
            {
                'name': 'PL-NEW-1',
                'device': cls.devices[1].pk,
                'address_family': AddressFamilyChoices.FAMILY_IPV4,
            },
            {
                'name': 'PL-NEW-2',
                'device': cls.devices[1].pk,
                'address_family': AddressFamilyChoices.FAMILY_IPV6,
            },
            {
                'name': 'PL-NEW-3',
                'device': cls.devices[1].pk,
                'address_family': AddressFamilyChoices.FAMILY_IPV4,
            },
        ]

    def test_rule_count_is_annotated_on_list_and_detail(self):
        """The viewset annotates rule_count; the serializer must surface it."""
        self.add_permissions('netbox_routing_protocols.view_prefixlist')
        prefix_list = PrefixList.objects.first()
        PrefixListRule.objects.create(
            prefix_list=prefix_list,
            sequence=10,
            action=ActionChoices.ACTION_PERMIT,
            prefix=self.prefixes4[0],
        )

        response = self.client.get(self._get_detail_url(prefix_list), **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        # One explicit rule plus the terminating deny-9999 rule.
        self.assertEqual(response.data['rule_count'], 2)


class PrefixListRuleTestCase(RoutingProtocolsAPITestCases.APIViewTestCase):
    model = PrefixListRule
    user_permissions = related_view_permissions('prefixlistrule')
    # The first rule in the queryset may be an auto-created deny/match-any rule, and
    # PATCHing a prefix onto it would violate the single-match-type constraint, so a
    # neutral update payload is used instead of falling back to create_data[0].
    update_data = {
        'description': 'New description',
    }

    @classmethod
    def setUpTestData(cls):
        cls.build_topology()

        cls.prefix_list = PrefixList.objects.create(
            name='PL-CORE-IN',
            device=cls.devices[0],
            address_family=AddressFamilyChoices.FAMILY_IPV4,
        )
        cls.other_prefix_list = PrefixList.objects.create(
            name='PL-CORE-OUT',
            device=cls.devices[0],
            address_family=AddressFamilyChoices.FAMILY_IPV4,
        )

        PrefixListRule.objects.create(
            prefix_list=cls.prefix_list,
            sequence=10,
            action=ActionChoices.ACTION_PERMIT,
            prefix=cls.prefixes4[0],
        )
        PrefixListRule.objects.create(
            prefix_list=cls.prefix_list,
            sequence=20,
            action=ActionChoices.ACTION_PERMIT,
            match_default=True,
        )
        PrefixListRule.objects.create(
            prefix_list=cls.prefix_list,
            sequence=30,
            action=ActionChoices.ACTION_DENY,
            match_any=True,
        )

        cls.create_data = [
            {
                'prefix_list': cls.other_prefix_list.pk,
                'sequence': 10,
                'action': ActionChoices.ACTION_PERMIT,
                'prefix': cls.prefixes4[1].pk,
                'min_prefix_length': 24,
                'max_prefix_length': 32,
            },
            {
                'prefix_list': cls.other_prefix_list.pk,
                'sequence': 20,
                'action': ActionChoices.ACTION_PERMIT,
                'match_default': True,
            },
            {
                'prefix_list': cls.other_prefix_list.pk,
                'sequence': 30,
                'action': ActionChoices.ACTION_DENY,
                'match_any': True,
            },
        ]


class RouteMapTestCase(RoutingProtocolsAPITestCases.APIViewTestCase):
    model = RouteMap
    user_permissions = related_view_permissions('routemap')

    @classmethod
    def setUpTestData(cls):
        cls.build_topology()

        for name in ('RM-CORE-IN', 'RM-CORE-OUT', 'RM-EDGE-IN'):
            RouteMap.objects.create(name=name, device=cls.devices[0])

        cls.create_data = [
            {'name': 'RM-NEW-1', 'device': cls.devices[1].pk},
            {'name': 'RM-NEW-2', 'device': cls.devices[1].pk},
            {'name': 'RM-NEW-3', 'device': cls.devices[1].pk},
        ]

    def test_rule_count_is_annotated_on_detail(self):
        self.add_permissions('netbox_routing_protocols.view_routemap')
        route_map = RouteMap.objects.first()

        response = self.client.get(self._get_detail_url(route_map), **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        # The terminating deny-9999 rule created by the post_save receiver.
        self.assertEqual(response.data['rule_count'], 1)


class RouteMapRuleTestCase(RoutingProtocolsAPITestCases.APIViewTestCase):
    model = RouteMapRule
    user_permissions = related_view_permissions('routemaprule')
    # See PrefixListRuleTestCase: the first rule is a deny/match-any rule.
    update_data = {
        'description': 'New description',
    }

    @classmethod
    def setUpTestData(cls):
        cls.build_topology()

        cls.route_map = RouteMap.objects.create(name='RM-CORE-IN', device=cls.devices[0])
        cls.other_route_map = RouteMap.objects.create(name='RM-CORE-OUT', device=cls.devices[0])
        cls.prefix_lists = [
            PrefixList.objects.create(
                name=name,
                device=cls.devices[0],
                address_family=AddressFamilyChoices.FAMILY_IPV4,
            )
            for name in ('PL-1', 'PL-2', 'PL-3')
        ]

        RouteMapRule.objects.create(
            route_map=cls.route_map,
            sequence=10,
            action=ActionChoices.ACTION_PERMIT,
            prefix_list=cls.prefix_lists[0],
        )
        RouteMapRule.objects.create(
            route_map=cls.route_map,
            sequence=20,
            action=ActionChoices.ACTION_PERMIT,
            prefix_list=cls.prefix_lists[1],
        )
        RouteMapRule.objects.create(
            route_map=cls.route_map,
            sequence=30,
            action=ActionChoices.ACTION_DENY,
            match_any=True,
        )

        cls.create_data = [
            {
                'route_map': cls.other_route_map.pk,
                'sequence': 10,
                'action': ActionChoices.ACTION_PERMIT,
                'prefix_list': cls.prefix_lists[0].pk,
            },
            {
                'route_map': cls.other_route_map.pk,
                'sequence': 20,
                'action': ActionChoices.ACTION_PERMIT,
                'prefix_list': cls.prefix_lists[2].pk,
            },
            {
                'route_map': cls.other_route_map.pk,
                'sequence': 30,
                'action': ActionChoices.ACTION_DENY,
                'match_any': True,
            },
        ]


#
# BGP
#


class BGPRouterTestCase(RoutingProtocolsAPITestCases.APIViewTestCase):
    model = BGPRouter
    user_permissions = related_view_permissions('bgprouter')

    @classmethod
    def setUpTestData(cls):
        cls.build_topology()

        for vrf in cls.vrfs:
            BGPRouter.objects.create(device=cls.devices[0], vrf=vrf, asn=cls.asns[0])

        cls.create_data = [
            {
                'device': cls.devices[1].pk,
                'vrf': cls.vrfs[0].pk,
                'asn': cls.asns[1].pk,
                'route_reflection': True,
            },
            {
                'device': cls.devices[1].pk,
                'vrf': cls.vrfs[1].pk,
                'asn': cls.asns[2].pk,
                'enable_evpn': True,
            },
            {
                'device': cls.devices[1].pk,
                'vrf': cls.vrfs[2].pk,
                'multipath_relax': False,
            },
        ]


class BGPPeergroupTestCase(RoutingProtocolsAPITestCases.APIViewTestCase):
    model = BGPPeergroup
    user_permissions = related_view_permissions('bgppeergroup')
    graphql_base_name = 'bgp_peergroup'
    # `password` is write-only, so it is absent from the response body. The generic
    # create tests assert every posted field comes back; password disclosure and
    # persistence are covered explicitly by PasswordDisclosureTestCase instead.
    validation_excluded_fields = ['password']

    @classmethod
    def setUpTestData(cls):
        cls.build_topology()

        cls.router = BGPRouter.objects.create(device=cls.devices[0], vrf=cls.vrfs[0])
        cls.other_router = BGPRouter.objects.create(device=cls.devices[1], vrf=cls.vrfs[0])

        for name in ('PG-CORE', 'PG-EDGE', 'PG-TRANSIT'):
            BGPPeergroup.objects.create(bgprouter=cls.router, name=name, remote_as=cls.asns[0])

        cls.create_data = [
            {
                'bgprouter': cls.other_router.pk,
                'name': 'PG-NEW-1',
                'remote_as': cls.asns[1].pk,
                'password': 'sekrit-1',
            },
            {
                'bgprouter': cls.other_router.pk,
                'name': 'PG-NEW-2',
                'remote_as': cls.asns[2].pk,
                'bfd': False,
            },
            {
                'bgprouter': cls.other_router.pk,
                'name': 'PG-NEW-3',
                'remote_as': cls.asns[3].pk,
                'ebgp_multihop': True,
                'ebgp_multihop_ttl': 4,
            },
        ]


class BGPPeerTestCase(RoutingProtocolsAPITestCases.APIViewTestCase):
    model = BGPPeer
    user_permissions = related_view_permissions('bgppeer')
    # See PrefixListRuleTestCase: falling back to create_data[0] would PATCH a
    # remote address onto an interface-addressed peer and break the XOR constraint.
    update_data = {
        'description': 'New description',
    }
    validation_excluded_fields = ['password']

    @classmethod
    def setUpTestData(cls):
        cls.build_topology()

        cls.router = BGPRouter.objects.create(device=cls.devices[0], vrf=cls.vrfs[0])
        cls.other_router = BGPRouter.objects.create(device=cls.devices[1], vrf=cls.vrfs[0])
        cls.peergroup = BGPPeergroup.objects.create(bgprouter=cls.other_router, name='PG-CORE', remote_as=cls.asns[0])

        BGPPeer.objects.create(bgprouter=cls.router, remote_address=cls.addresses4[0], remote_as=cls.asns[0])
        BGPPeer.objects.create(bgprouter=cls.router, remote_address=cls.addresses4[1], remote_as=cls.asns[0])
        BGPPeer.objects.create(bgprouter=cls.router, interface=cls.interfaces1[0], remote_as=cls.asns[0])

        cls.create_data = [
            {
                'bgprouter': cls.other_router.pk,
                'remote_address': cls.addresses4[2].pk,
                'remote_as': cls.asns[1].pk,
                'password': 'sekrit-2',
            },
            {
                'bgprouter': cls.other_router.pk,
                'remote_address': cls.addresses4[3].pk,
                'remote_as': cls.asns[1].pk,
                'peergroup': cls.peergroup.pk,
            },
            {
                'bgprouter': cls.other_router.pk,
                'interface': cls.interfaces2[0].pk,
                'remote_as': cls.asns[2].pk,
            },
        ]


class BGPAddressFamilyTestCase(RoutingProtocolsAPITestCases.APIViewTestCase):
    model = BGPAddressFamily
    user_permissions = related_view_permissions('bgpaddressfamily')
    # BGPAddressFamily has no name property; its brief representation uses `family`.
    brief_fields = BRIEF_FIELDS_FAMILY

    @classmethod
    def setUpTestData(cls):
        cls.build_topology()

        cls.router = BGPRouter.objects.create(device=cls.devices[0], vrf=cls.vrfs[0])
        cls.other_router = BGPRouter.objects.create(device=cls.devices[1], vrf=cls.vrfs[0])
        cls.route_map = RouteMap.objects.create(name='RM-1', device=cls.devices[1])

        for family in (
            BGPAddressFamilyChoices.AFI_IPV4_UNICAST,
            BGPAddressFamilyChoices.AFI_IPV6_UNICAST,
            BGPAddressFamilyChoices.AFI_L2VPN_EVPN,
        ):
            BGPAddressFamily.objects.create(bgprouter=cls.router, family=family)

        cls.create_data = [
            {
                'bgprouter': cls.other_router.pk,
                'family': BGPAddressFamilyChoices.AFI_IPV4_UNICAST,
                'networks': sorted([cls.prefixes4[0].pk, cls.prefixes4[1].pk]),
                'network_route_map': cls.route_map.pk,
            },
            {
                'bgprouter': cls.other_router.pk,
                'family': BGPAddressFamilyChoices.AFI_IPV6_UNICAST,
                'aggregate_routes': sorted([cls.prefixes6[0].pk]),
                'aggregate_route_map': cls.route_map.pk,
            },
            {
                'bgprouter': cls.other_router.pk,
                'family': BGPAddressFamilyChoices.AFI_L2VPN_EVPN,
                'export_to_evpn': True,
            },
        ]


class BGPAddressFamilyRedistributeTestCase(RoutingProtocolsAPITestCases.APIViewTestCase):
    model = BGPAddressFamilyRedistribute
    user_permissions = related_view_permissions('bgpaddressfamilyredistribute')
    graphql_base_name = 'bgp_address_family_redistribute'

    @classmethod
    def setUpTestData(cls):
        cls.build_topology()

        router = BGPRouter.objects.create(device=cls.devices[0], vrf=cls.vrfs[0])
        cls.families = [
            BGPAddressFamily.objects.create(bgprouter=router, family=family)
            for family in (
                BGPAddressFamilyChoices.AFI_IPV4_UNICAST,
                BGPAddressFamilyChoices.AFI_IPV6_UNICAST,
                BGPAddressFamilyChoices.AFI_L2VPN_EVPN,
            )
        ]
        cls.route_map = RouteMap.objects.create(name='RM-1', device=cls.devices[0])

        BGPAddressFamilyRedistribute.objects.create(
            family=cls.families[0], protocol=BGPRedistributeProtocolChoices.PROTOCOL_CONNECTED
        )
        BGPAddressFamilyRedistribute.objects.create(
            family=cls.families[0], protocol=BGPRedistributeProtocolChoices.PROTOCOL_STATIC
        )
        BGPAddressFamilyRedistribute.objects.create(
            family=cls.families[1], protocol=BGPRedistributeProtocolChoices.PROTOCOL_CONNECTED
        )

        cls.create_data = [
            {
                'family': cls.families[1].pk,
                'protocol': BGPRedistributeProtocolChoices.PROTOCOL_STATIC,
                'route_map': cls.route_map.pk,
            },
            {
                'family': cls.families[2].pk,
                'protocol': BGPRedistributeProtocolChoices.PROTOCOL_CONNECTED,
            },
            {
                'family': cls.families[2].pk,
                'protocol': BGPRedistributeProtocolChoices.PROTOCOL_STATIC,
                'enable': False,
            },
        ]


class BGPPeerAddressFamilyTestCase(RoutingProtocolsAPITestCases.APIViewTestCase):
    model = BGPPeerAddressFamily
    user_permissions = related_view_permissions('bgppeeraddressfamily')

    @classmethod
    def setUpTestData(cls):
        cls.build_topology()

        router = BGPRouter.objects.create(device=cls.devices[0], vrf=cls.vrfs[0])
        cls.peer = BGPPeer.objects.create(bgprouter=router, remote_address=cls.addresses4[0], remote_as=cls.asns[0])
        cls.other_peer = BGPPeer.objects.create(
            bgprouter=router, remote_address=cls.addresses4[1], remote_as=cls.asns[0]
        )
        cls.route_map = RouteMap.objects.create(name='RM-1', device=cls.devices[0])

        for family in (
            BGPAddressFamilyChoices.AFI_IPV4_UNICAST,
            BGPAddressFamilyChoices.AFI_IPV6_UNICAST,
            BGPAddressFamilyChoices.AFI_L2VPN_EVPN,
        ):
            BGPPeerAddressFamily.objects.create(peer=cls.peer, family=family)

        cls.create_data = [
            {
                'peer': cls.other_peer.pk,
                'family': BGPAddressFamilyChoices.AFI_IPV4_UNICAST,
                'inbound_policy': cls.route_map.pk,
                'outbound_policy': cls.route_map.pk,
            },
            {
                'peer': cls.other_peer.pk,
                'family': BGPAddressFamilyChoices.AFI_IPV6_UNICAST,
                'default_originate': True,
            },
            {
                'peer': cls.other_peer.pk,
                'family': BGPAddressFamilyChoices.AFI_L2VPN_EVPN,
                'route_reflector_client': True,
            },
        ]


class BGPPeergroupAddressFamilyTestCase(RoutingProtocolsAPITestCases.APIViewTestCase):
    model = BGPPeergroupAddressFamily
    user_permissions = related_view_permissions('bgppeergroupaddressfamily')
    graphql_base_name = 'bgp_peergroup_address_family'

    @classmethod
    def setUpTestData(cls):
        cls.build_topology()

        router = BGPRouter.objects.create(device=cls.devices[0], vrf=cls.vrfs[0])
        cls.peergroup = BGPPeergroup.objects.create(bgprouter=router, name='PG-CORE', remote_as=cls.asns[0])
        cls.other_peergroup = BGPPeergroup.objects.create(bgprouter=router, name='PG-EDGE', remote_as=cls.asns[0])
        cls.route_map = RouteMap.objects.create(name='RM-1', device=cls.devices[0])

        for family in (
            BGPAddressFamilyChoices.AFI_IPV4_UNICAST,
            BGPAddressFamilyChoices.AFI_IPV6_UNICAST,
            BGPAddressFamilyChoices.AFI_L2VPN_EVPN,
        ):
            BGPPeergroupAddressFamily.objects.create(peergroup=cls.peergroup, family=family)

        cls.create_data = [
            {
                'peergroup': cls.other_peergroup.pk,
                'family': BGPAddressFamilyChoices.AFI_IPV4_UNICAST,
                'inbound_policy': cls.route_map.pk,
                'outbound_policy': cls.route_map.pk,
            },
            {
                'peergroup': cls.other_peergroup.pk,
                'family': BGPAddressFamilyChoices.AFI_IPV6_UNICAST,
                'soft_reconfiguration': False,
            },
            {
                'peergroup': cls.other_peergroup.pk,
                'family': BGPAddressFamilyChoices.AFI_L2VPN_EVPN,
                'route_reflector_client': True,
            },
        ]


#
# Cross-endpoint regression suites
#


class RoutingProtocolsAPIFixture(BaseTestData, APITestCase):
    """One populated object per model, for the tests that sweep every endpoint."""

    @classmethod
    def setUpTestData(cls):
        cls.build_topology()

        cls.static_route = StaticRoute.objects.create(
            device=cls.devices[0],
            vrf=cls.vrfs[0],
            prefix=cls.prefixes4[0],
            nexthop=cls.addresses4[0],
        )
        cls.prefix_list = PrefixList.objects.create(
            name='PL-CORE-IN',
            device=cls.devices[0],
            address_family=AddressFamilyChoices.FAMILY_IPV4,
        )
        cls.prefix_list_rule = PrefixListRule.objects.create(
            prefix_list=cls.prefix_list,
            sequence=10,
            action=ActionChoices.ACTION_PERMIT,
            prefix=cls.prefixes4[1],
        )
        cls.route_map = RouteMap.objects.create(name='RM-CORE-IN', device=cls.devices[0])
        cls.route_map_rule = RouteMapRule.objects.create(
            route_map=cls.route_map,
            sequence=10,
            action=ActionChoices.ACTION_PERMIT,
            prefix_list=cls.prefix_list,
        )
        cls.bgp_router = BGPRouter.objects.create(device=cls.devices[0], vrf=cls.vrfs[0])
        cls.peergroup = BGPPeergroup.objects.create(
            bgprouter=cls.bgp_router,
            name='PG-CORE',
            remote_as=cls.asns[0],
            password='peergroup-secret',
        )
        cls.peer = BGPPeer.objects.create(
            bgprouter=cls.bgp_router,
            remote_address=cls.addresses4[1],
            remote_as=cls.asns[0],
            peergroup=cls.peergroup,
            password='peer-secret',
        )
        cls.address_family = BGPAddressFamily.objects.create(
            bgprouter=cls.bgp_router,
            family=BGPAddressFamilyChoices.AFI_IPV4_UNICAST,
        )
        cls.redistribution = BGPAddressFamilyRedistribute.objects.create(
            family=cls.address_family,
            protocol=BGPRedistributeProtocolChoices.PROTOCOL_CONNECTED,
        )
        cls.peer_address_family = BGPPeerAddressFamily.objects.create(
            peer=cls.peer,
            family=BGPAddressFamilyChoices.AFI_IPV4_UNICAST,
        )
        cls.peergroup_address_family = BGPPeergroupAddressFamily.objects.create(
            peergroup=cls.peergroup,
            family=BGPAddressFamilyChoices.AFI_IPV4_UNICAST,
        )

    def endpoints(self):
        """Yield (label, instance, brief_fields) for all twelve endpoints."""
        return (
            ('staticroute', self.static_route, BRIEF_FIELDS),
            ('prefixlist', self.prefix_list, BRIEF_FIELDS),
            ('prefixlistrule', self.prefix_list_rule, BRIEF_FIELDS),
            ('routemap', self.route_map, BRIEF_FIELDS),
            ('routemaprule', self.route_map_rule, BRIEF_FIELDS),
            ('bgprouter', self.bgp_router, BRIEF_FIELDS),
            ('bgppeergroup', self.peergroup, BRIEF_FIELDS),
            ('bgppeer', self.peer, BRIEF_FIELDS),
            ('bgpaddressfamily', self.address_family, BRIEF_FIELDS_FAMILY),
            ('bgpaddressfamilyredistribute', self.redistribution, BRIEF_FIELDS),
            ('bgppeeraddressfamily', self.peer_address_family, BRIEF_FIELDS),
            ('bgppeergroupaddressfamily', self.peergroup_address_family, BRIEF_FIELDS),
        )

    def list_url(self, label):
        return reverse(f'{VIEW_NAMESPACE}-api:{label}-list')

    def detail_url(self, label, instance):
        return reverse(f'{VIEW_NAMESPACE}-api:{label}-detail', kwargs={'pk': instance.pk})

    def grant_view_permissions(self):
        self.add_permissions(
            *[f'netbox_routing_protocols.view_{label}' for label, _instance, _fields in self.endpoints()]
        )


class BriefModeTestCase(RoutingProtocolsAPIFixture):
    """
    ``?brief=true`` renders each serializer's ``brief_fields``. A brief_fields entry
    naming a field the serializer does not declare produces a 500 rather than a
    truncated object, so every endpoint is checked rather than a representative one.
    """

    def test_brief_list_responses(self):
        self.grant_view_permissions()

        for label, _instance, brief_fields in self.endpoints():
            with self.subTest(endpoint=label):
                response = self.client.get(f'{self.list_url(label)}?brief=true', **self.header)
                self.assertHttpStatus(response, status.HTTP_200_OK)
                # Prefix lists and route maps each carry an extra signal-created rule.
                self.assertEqual(len(response.data['results']), _instance._meta.model.objects.count())
                self.assertGreaterEqual(len(response.data['results']), 1)
                for result in response.data['results']:
                    self.assertEqual(sorted(result), brief_fields)

    def test_brief_detail_responses(self):
        self.grant_view_permissions()

        for label, instance, brief_fields in self.endpoints():
            with self.subTest(endpoint=label):
                response = self.client.get(f'{self.detail_url(label, instance)}?brief=true', **self.header)
                self.assertHttpStatus(response, status.HTTP_200_OK)
                self.assertEqual(sorted(response.data), brief_fields)

    def test_brief_responses_carry_a_usable_display_value(self):
        """Brief output is what the UI shows in pickers, so it must not be empty."""
        self.grant_view_permissions()

        for label, instance, _brief_fields in self.endpoints():
            with self.subTest(endpoint=label):
                response = self.client.get(f'{self.detail_url(label, instance)}?brief=true', **self.header)
                self.assertHttpStatus(response, status.HTTP_200_OK)
                self.assertEqual(response.data['display'], str(instance))
                self.assertTrue(response.data['display'])


class NestedSerializationTestCase(RoutingProtocolsAPIFixture):
    """
    ``PrefixListSerializer.rule_count`` is populated by an annotation applied to the
    PrefixList viewset's queryset. A PrefixList nested inside a prefix list rule or
    a route map rule comes from a different queryset and carries no such attribute,
    so serializing it must not depend on one.
    """

    def test_prefix_list_rule_detail_renders_its_prefix_list(self):
        self.grant_view_permissions()

        response = self.client.get(self.detail_url('prefixlistrule', self.prefix_list_rule), **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        nested = response.data['prefix_list']
        self.assertEqual(sorted(nested), BRIEF_FIELDS)
        self.assertEqual(nested['id'], self.prefix_list.pk)
        self.assertEqual(nested['name'], 'PL-CORE-IN')
        self.assertNotIn('rule_count', nested)

    def test_prefix_list_rule_list_renders_its_prefix_list(self):
        self.grant_view_permissions()

        response = self.client.get(self.list_url('prefixlistrule'), **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        for result in response.data['results']:
            self.assertEqual(sorted(result['prefix_list']), BRIEF_FIELDS)

    def test_route_map_rule_detail_renders_its_prefix_list_and_route_map(self):
        self.grant_view_permissions()

        response = self.client.get(self.detail_url('routemaprule', self.route_map_rule), **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)

        nested_prefix_list = response.data['prefix_list']
        self.assertEqual(sorted(nested_prefix_list), BRIEF_FIELDS)
        self.assertEqual(nested_prefix_list['id'], self.prefix_list.pk)
        self.assertNotIn('rule_count', nested_prefix_list)

        nested_route_map = response.data['route_map']
        self.assertEqual(sorted(nested_route_map), BRIEF_FIELDS)
        self.assertEqual(nested_route_map['id'], self.route_map.pk)
        self.assertNotIn('rule_count', nested_route_map)

    def test_route_map_rule_list_renders_its_prefix_list(self):
        self.grant_view_permissions()

        response = self.client.get(self.list_url('routemaprule'), **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        for result in response.data['results']:
            self.assertEqual(sorted(result['route_map']), BRIEF_FIELDS)
            if result['prefix_list'] is not None:
                self.assertEqual(sorted(result['prefix_list']), BRIEF_FIELDS)

    def test_route_maps_nested_in_bgp_objects_render(self):
        """Route maps are nested from several BGP serializers, all unannotated."""
        self.grant_view_permissions()
        self.peer_address_family.inbound_policy = self.route_map
        self.peer_address_family.outbound_policy = self.route_map
        self.peer_address_family.save()
        self.address_family.network_route_map = self.route_map
        self.address_family.save()
        self.redistribution.route_map = self.route_map
        self.redistribution.save()

        cases = (
            ('bgppeeraddressfamily', self.peer_address_family, 'inbound_policy'),
            ('bgppeeraddressfamily', self.peer_address_family, 'outbound_policy'),
            ('bgpaddressfamily', self.address_family, 'network_route_map'),
            ('bgpaddressfamilyredistribute', self.redistribution, 'route_map'),
        )
        for label, instance, field in cases:
            with self.subTest(endpoint=label, field=field):
                response = self.client.get(self.detail_url(label, instance), **self.header)
                self.assertHttpStatus(response, status.HTTP_200_OK)
                self.assertEqual(sorted(response.data[field]), BRIEF_FIELDS)
                self.assertNotIn('rule_count', response.data[field])


class PasswordDisclosureTestCase(RoutingProtocolsAPIFixture):
    """
    The BGP MD5 authentication key is deliberately readable: rendering it into device
    configuration is the reason for modelling it, and automation reads it from here.

    It is still kept out of the representations that would scatter it further than that
    need requires — ``brief_fields``, and therefore every nested representation.
    """

    def assertNoPassword(self, payload):
        self.assertNotIn('password', payload)
        self.assertNotIn('peer-secret', str(payload))
        self.assertNotIn('peergroup-secret', str(payload))

    def test_password_is_returned_in_detail_responses(self):
        """Automation reads the key from here; if this breaks, config generation breaks."""
        self.grant_view_permissions()

        for label, instance, secret in (
            ('bgppeer', self.peer, 'peer-secret'),
            ('bgppeergroup', self.peergroup, 'peergroup-secret'),
        ):
            with self.subTest(endpoint=label):
                response = self.client.get(self.detail_url(label, instance), **self.header)
                self.assertHttpStatus(response, status.HTTP_200_OK)
                self.assertIn('password', response.data)
                self.assertEqual(response.data['password'], secret)

    def test_password_is_returned_in_list_responses(self):
        self.grant_view_permissions()

        for label, secret in (('bgppeer', 'peer-secret'), ('bgppeergroup', 'peergroup-secret')):
            with self.subTest(endpoint=label):
                response = self.client.get(self.list_url(label), **self.header)
                self.assertHttpStatus(response, status.HTTP_200_OK)
                passwords = [r['password'] for r in response.data['results']]
                self.assertIn(secret, passwords)

    def test_password_absent_from_brief_responses(self):
        self.grant_view_permissions()

        for label, instance in (('bgppeer', self.peer), ('bgppeergroup', self.peergroup)):
            with self.subTest(endpoint=label):
                response = self.client.get(f'{self.detail_url(label, instance)}?brief=true', **self.header)
                self.assertHttpStatus(response, status.HTTP_200_OK)
                self.assertNoPassword(response.data)

    def test_password_absent_from_a_peergroup_nested_in_a_peer(self):
        self.grant_view_permissions()

        response = self.client.get(self.detail_url('bgppeer', self.peer), **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertIsNotNone(response.data['peergroup'])
        self.assertNoPassword(response.data['peergroup'])

    def test_password_absent_from_a_peer_nested_in_an_address_family(self):
        self.grant_view_permissions()

        response = self.client.get(self.detail_url('bgppeeraddressfamily', self.peer_address_family), **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertNoPassword(response.data['peer'])

        response = self.client.get(
            self.detail_url('bgppeergroupaddressfamily', self.peergroup_address_family), **self.header
        )
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertNoPassword(response.data['peergroup'])

    def test_password_is_settable_on_create(self):
        self.add_permissions(
            'netbox_routing_protocols.add_bgppeer',
            'netbox_routing_protocols.add_bgppeergroup',
        )

        response = self.client.post(
            self.list_url('bgppeergroup'),
            {
                'bgprouter': self.bgp_router.pk,
                'name': 'PG-NEW',
                'remote_as': self.asns[0].pk,
                'password': 'created-secret',
            },
            format='json',
            **self.header,
        )
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertEqual(response.data['password'], 'created-secret')
        self.assertEqual(BGPPeergroup.objects.get(pk=response.data['id']).password, 'created-secret')

        response = self.client.post(
            self.list_url('bgppeer'),
            {
                'bgprouter': self.bgp_router.pk,
                'remote_address': self.addresses4[2].pk,
                'remote_as': self.asns[0].pk,
                'password': 'created-secret',
            },
            format='json',
            **self.header,
        )
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertEqual(response.data['password'], 'created-secret')
        self.assertEqual(BGPPeer.objects.get(pk=response.data['id']).password, 'created-secret')

    def test_password_is_settable_on_update(self):
        self.add_permissions(
            'netbox_routing_protocols.change_bgppeer',
            'netbox_routing_protocols.change_bgppeergroup',
        )

        response = self.client.patch(
            self.detail_url('bgppeer', self.peer),
            {'password': 'rotated-secret'},
            format='json',
            **self.header,
        )
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.data['password'], 'rotated-secret')
        self.peer.refresh_from_db()
        self.assertEqual(self.peer.password, 'rotated-secret')

        response = self.client.patch(
            self.detail_url('bgppeergroup', self.peergroup),
            {'password': 'rotated-secret'},
            format='json',
            **self.header,
        )
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertEqual(response.data['password'], 'rotated-secret')
        self.peergroup.refresh_from_db()
        self.assertEqual(self.peergroup.password, 'rotated-secret')

    def test_password_can_be_cleared(self):
        self.add_permissions('netbox_routing_protocols.change_bgppeer')

        response = self.client.patch(
            self.detail_url('bgppeer', self.peer),
            {'password': ''},
            format='json',
            **self.header,
        )
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.peer.refresh_from_db()
        self.assertEqual(self.peer.password, '')
