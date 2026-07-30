"""
FilterSet tests.

The headline concern is free-text search. ``?q=`` accepts whatever a user types,
and two ways of writing it have failed in the past: referencing a field the model
does not have, and handing arbitrary text to PostgreSQL's CIDR containment
operator, which errors on anything that is not a valid network. ``SEARCH_VALUES``
below therefore mixes ordinary words, address-shaped strings, punctuation and an
empty string, and every filterset is run against all of them.

The rest is per-filterset coverage of the declared filters, plus NetBox's own
``ChangeLoggedFilterSetTests``, which audits each filterset for filters the model
fields imply.
"""

from django.test import TestCase

from utilities.testing import ChangeLoggedFilterSetTests

from netbox_routing_protocols.choices import (
    ActionChoices,
    AddressFamilyChoices,
    BGPAddressFamilyChoices,
    BGPCommunityTypeChoices,
    BGPRedistributeProtocolChoices,
)
from netbox_routing_protocols.filtersets import (
    BFDProfileFilterSet,
    BGPAddressFamilyFilterSet,
    BGPAddressFamilyRedistributeFilterSet,
    BGPCommunityFilterSet,
    BGPCommunityListFilterSet,
    BGPCommunityListRuleFilterSet,
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
    BGPCommunity,
    BGPCommunityList,
    BGPCommunityListRule,
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

# Inputs every filterset's `q` filter is run against. Each one has broken something
# somewhere: bare words hit filtersets searching a non-existent column, and the
# address-shaped and punctuation-only values hit filtersets applying a CIDR
# operator to text.
SEARCH_VALUES = (
    'core',  # ordinary text; matches the fixture device names
    'CORE',  # ...and case-insensitively
    'PL-CORE-IN',  # an object name, with punctuation
    '10.123',  # a partial IPv4 address
    '10.123.1.0/24',  # a complete IPv4 prefix
    '10.123.1.1',  # an IPv4 host address
    '2001:db8::/32',  # an IPv6 prefix
    '2001:db8:1::1',  # an IPv6 host address
    '::',  # degenerate, but still address-shaped
    '/',  # a lone separator
    '.',  # ...and another
    '65000',  # an AS number
    '9' * 24,  # a number far too large for the bigint AS column
    'not-a-prefix',  # text that is emphatically not an address
    '%',  # a SQL wildcard
    '_',  # ...and the single-character one
    "o'brien",  # an apostrophe
    '  core  ',  # surrounding whitespace
    '',  # nothing at all
)


class NoPasswordFilterTests:
    """
    The BGP MD5 key must not be filterable.

    NetBox's filter audit expects a filter for every model field, but exposing one
    for `password` would turn the list endpoint into an oracle: `?password__isw=a`
    recovers the key one character at a time. The field is excluded from the audit
    and its absence asserted instead.
    """

    def test_password_is_not_filterable(self):
        matches = [name for name in self.filterset.get_filters() if 'password' in name]
        self.assertEqual(matches, [])


class FreeTextSearchTests:
    """
    ``?q=`` must return a queryset for any input, never raise.

    Mixed into every filterset test case below.
    """

    def test_search_accepts_any_input(self):
        for value in SEARCH_VALUES:
            with self.subTest(value=value):
                # count() forces the query to be executed against PostgreSQL, which
                # is where a bad lookup or a CIDR cast would blow up.
                self.assertGreaterEqual(self.filterset({'q': value}, self.queryset).qs.count(), 0)

    def test_search_ignores_an_empty_term(self):
        for value in ('', '   '):
            with self.subTest(value=value):
                self.assertEqual(
                    self.filterset({'q': value}, self.queryset).qs.count(),
                    self.queryset.count(),
                )


class FilterSetTestData(BaseTestData):
    """
    One shared object graph for all twelve filterset test cases.

    Every model gets at least three instances so NetBox's ``test_id`` (which
    requires more than two) and the created/last_updated tests have something to
    work with.
    """

    @classmethod
    def build_objects(cls):
        cls.build_topology()

        cls.static_routes = [
            StaticRoute.objects.create(
                device=cls.devices[0], vrf=cls.vrfs[0], prefix=cls.prefixes4[0], nexthop=cls.addresses4[0]
            ),
            StaticRoute.objects.create(
                device=cls.devices[0], vrf=cls.vrfs[0], prefix=cls.prefixes6[0], nexthop=cls.addresses6[0]
            ),
            StaticRoute.objects.create(
                device=cls.devices[0], vrf=cls.vrfs[0], nexthop=cls.addresses4[1], default_route=True
            ),
            StaticRoute.objects.create(
                device=cls.devices[1], vrf=cls.vrfs[1], prefix=cls.prefixes4[1], nexthop=cls.addresses4[2]
            ),
        ]

        cls.prefix_lists = [
            PrefixList.objects.create(
                name='PL-CORE-IN', device=cls.devices[0], address_family=AddressFamilyChoices.FAMILY_IPV4
            ),
            PrefixList.objects.create(
                name='PL-CORE-OUT', device=cls.devices[0], address_family=AddressFamilyChoices.FAMILY_IPV6
            ),
            PrefixList.objects.create(
                name='PL-EDGE-IN', device=cls.devices[1], address_family=AddressFamilyChoices.FAMILY_IPV4
            ),
        ]
        # Each prefix list above also carries a signal-created deny-9999 rule.
        cls.prefix_list_rules = [
            PrefixListRule.objects.create(
                prefix_list=cls.prefix_lists[0],
                sequence=10,
                action=ActionChoices.ACTION_PERMIT,
                prefix=cls.prefixes4[0],
                min_prefix_length=24,
                max_prefix_length=32,
            ),
            PrefixListRule.objects.create(
                prefix_list=cls.prefix_lists[0],
                sequence=20,
                action=ActionChoices.ACTION_PERMIT,
                match_default=True,
            ),
            PrefixListRule.objects.create(
                prefix_list=cls.prefix_lists[2],
                sequence=10,
                action=ActionChoices.ACTION_DENY,
                prefix=cls.prefixes4[1],
            ),
        ]

        cls.route_maps = [
            RouteMap.objects.create(name='RM-CORE-IN', device=cls.devices[0]),
            RouteMap.objects.create(name='RM-CORE-OUT', device=cls.devices[0]),
            RouteMap.objects.create(name='RM-EDGE-IN', device=cls.devices[1]),
        ]
        cls.route_map_rules = [
            RouteMapRule.objects.create(
                route_map=cls.route_maps[0],
                sequence=10,
                action=ActionChoices.ACTION_PERMIT,
                prefix_list=cls.prefix_lists[0],
            ),
            RouteMapRule.objects.create(
                route_map=cls.route_maps[0],
                sequence=20,
                action=ActionChoices.ACTION_PERMIT,
                match_any=True,
            ),
            RouteMapRule.objects.create(
                route_map=cls.route_maps[2],
                sequence=10,
                action=ActionChoices.ACTION_DENY,
                prefix_list=cls.prefix_lists[2],
            ),
        ]

        cls.bgp_routers = [
            BGPRouter.objects.create(device=cls.devices[0], vrf=cls.vrfs[0], asn=cls.asns[0]),
            BGPRouter.objects.create(device=cls.devices[0], vrf=cls.vrfs[1], asn=cls.asns[1], route_reflection=True),
            BGPRouter.objects.create(device=cls.devices[1], vrf=cls.vrfs[0], asn=cls.asns[2], enable=False),
        ]

        cls.bfd_profiles = [
            BFDProfile.objects.create(name='BFD-FAST', min_tx=100, min_rx=100),
            BFDProfile.objects.create(name='BFD-SLOW', device=cls.devices[0], min_tx=1000, min_rx=1000),
            BFDProfile.objects.create(name='BFD-ECHO', echo_mode=True),
        ]

        cls.communities = [
            BGPCommunity.objects.create(value='65001:100', name='CUSTOMERS'),
            BGPCommunity.objects.create(value='rt:65001:200', type=BGPCommunityTypeChoices.TYPE_EXTENDED),
            BGPCommunity.objects.create(value='65001:1:1', type=BGPCommunityTypeChoices.TYPE_LARGE),
        ]
        cls.community_lists = [
            BGPCommunityList.objects.create(name='CL-CORE', device=cls.devices[0]),
            BGPCommunityList.objects.create(name='CL-EDGE', device=cls.devices[1]),
            BGPCommunityList.objects.create(name='CL-SHARED'),
        ]
        cls.community_list_rules = [
            BGPCommunityListRule.objects.create(
                community_list=cls.community_lists[0],
                sequence=10,
                action=ActionChoices.ACTION_PERMIT,
                community=cls.communities[0],
            ),
            BGPCommunityListRule.objects.create(
                community_list=cls.community_lists[0],
                sequence=20,
                action=ActionChoices.ACTION_DENY,
                community=cls.communities[1],
            ),
            BGPCommunityListRule.objects.create(
                community_list=cls.community_lists[2],
                sequence=10,
                action=ActionChoices.ACTION_PERMIT,
                community=cls.communities[0],
            ),
        ]

        cls.peergroups = [
            BGPPeergroup.objects.create(
                bgprouter=cls.bgp_routers[0], name='PG-CORE', remote_as=cls.asns[0], bfd=cls.bfd_profiles[0]
            ),
            BGPPeergroup.objects.create(bgprouter=cls.bgp_routers[0], name='PG-EDGE', remote_as=cls.asns[1]),
            BGPPeergroup.objects.create(bgprouter=cls.bgp_routers[2], name='PG-TRANSIT', remote_as=cls.asns[2]),
        ]

        cls.peers = [
            BGPPeer.objects.create(
                bgprouter=cls.bgp_routers[0],
                remote_address=cls.addresses4[0],
                remote_as=cls.asns[0],
                peergroup=cls.peergroups[0],
            ),
            BGPPeer.objects.create(
                bgprouter=cls.bgp_routers[0],
                remote_address=cls.addresses6[0],
                remote_as=cls.asns[1],
            ),
            BGPPeer.objects.create(
                bgprouter=cls.bgp_routers[0],
                interface=cls.interfaces1[0],
                remote_as=cls.asns[2],
                enable=False,
            ),
        ]

        cls.address_families = [
            BGPAddressFamily.objects.create(
                bgprouter=cls.bgp_routers[0],
                family=BGPAddressFamilyChoices.AFI_IPV4_UNICAST,
                network_route_map=cls.route_maps[0],
            ),
            BGPAddressFamily.objects.create(
                bgprouter=cls.bgp_routers[0],
                family=BGPAddressFamilyChoices.AFI_IPV6_UNICAST,
                aggregate_route_map=cls.route_maps[1],
            ),
            BGPAddressFamily.objects.create(
                bgprouter=cls.bgp_routers[1],
                family=BGPAddressFamilyChoices.AFI_L2VPN_EVPN,
                export_to_evpn=True,
            ),
        ]
        # Aggregates and network statements overlap deliberately: prefixes4[2] is a
        # network on two families, and families[0] aggregates two prefixes, so the
        # many-to-many filters are exercised against both fan-out directions.
        cls.address_families[0].aggregate_routes.set([cls.prefixes4[0], cls.prefixes4[1]])
        cls.address_families[0].networks.set([cls.prefixes4[2]])
        cls.address_families[1].aggregate_routes.set([cls.prefixes6[0]])
        cls.address_families[1].networks.set([cls.prefixes4[2], cls.prefixes6[1]])

        cls.redistributions = [
            BGPAddressFamilyRedistribute.objects.create(
                family=cls.address_families[0],
                protocol=BGPRedistributeProtocolChoices.PROTOCOL_CONNECTED,
                route_map=cls.route_maps[0],
            ),
            BGPAddressFamilyRedistribute.objects.create(
                family=cls.address_families[0],
                protocol=BGPRedistributeProtocolChoices.PROTOCOL_STATIC,
            ),
            BGPAddressFamilyRedistribute.objects.create(
                family=cls.address_families[1],
                protocol=BGPRedistributeProtocolChoices.PROTOCOL_CONNECTED,
                enable=False,
            ),
        ]

        cls.peer_families = [
            BGPPeerAddressFamily.objects.create(
                peer=cls.peers[0],
                family=BGPAddressFamilyChoices.AFI_IPV4_UNICAST,
                inbound_policy=cls.route_maps[0],
            ),
            BGPPeerAddressFamily.objects.create(
                peer=cls.peers[0],
                family=BGPAddressFamilyChoices.AFI_IPV6_UNICAST,
                default_originate=True,
            ),
            BGPPeerAddressFamily.objects.create(
                peer=cls.peers[1],
                family=BGPAddressFamilyChoices.AFI_IPV4_UNICAST,
                enable=False,
            ),
        ]

        cls.peergroup_families = [
            BGPPeergroupAddressFamily.objects.create(
                peergroup=cls.peergroups[0],
                family=BGPAddressFamilyChoices.AFI_IPV4_UNICAST,
                outbound_policy=cls.route_maps[0],
            ),
            BGPPeergroupAddressFamily.objects.create(
                peergroup=cls.peergroups[0],
                family=BGPAddressFamilyChoices.AFI_IPV6_UNICAST,
                route_reflector_client=True,
            ),
            BGPPeergroupAddressFamily.objects.create(
                peergroup=cls.peergroups[1],
                family=BGPAddressFamilyChoices.AFI_IPV4_UNICAST,
                soft_reconfiguration=False,
            ),
        ]

    @classmethod
    def setUpTestData(cls):
        cls.build_objects()


#
# Static routing
#


class StaticRouteFilterSetTestCase(FilterSetTestData, FreeTextSearchTests, ChangeLoggedFilterSetTests, TestCase):
    queryset = StaticRoute.objects.all()
    filterset = StaticRouteFilterSet

    def test_device(self):
        params = {'device_id': [self.devices[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)
        params = {'device': [self.devices[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_vrf(self):
        params = {'vrf_id': [self.vrfs[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)
        params = {'vrf': [self.vrfs[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_prefix(self):
        params = {'prefix_id': [self.prefixes4[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_nexthop(self):
        params = {'nexthop_id': [self.addresses4[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_default_route(self):
        params = {'default_route': True}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_search_matches_device_name(self):
        self.assertEqual(self.filterset({'q': 'core-sw2'}, self.queryset).qs.count(), 1)

    def test_search_matches_prefix(self):
        self.assertGreaterEqual(self.filterset({'q': '10.123.1.0'}, self.queryset).qs.count(), 1)


#
# Routing policy
#


class BFDProfileFilterSetTestCase(FilterSetTestData, FreeTextSearchTests, ChangeLoggedFilterSetTests, TestCase):
    queryset = BFDProfile.objects.all()
    filterset = BFDProfileFilterSet

    def test_name(self):
        params = {'name': ['BFD-FAST']}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_device(self):
        params = {'device_id': [self.devices[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_available_on_device(self):
        # The device's own profile plus the two shared ones.
        params = {'available_on_device': [self.devices[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_shared(self):
        self.assertEqual(self.filterset({'shared': True}, self.queryset).qs.count(), 2)
        self.assertEqual(self.filterset({'shared': False}, self.queryset).qs.count(), 1)

    def test_intervals(self):
        self.assertEqual(self.filterset({'min_tx': [100]}, self.queryset).qs.count(), 1)
        self.assertEqual(self.filterset({'detect_multiplier': [3]}, self.queryset).qs.count(), 0)

    def test_echo_mode(self):
        self.assertEqual(self.filterset({'echo_mode': True}, self.queryset).qs.count(), 1)

    def test_search_matches_name(self):
        self.assertEqual(self.filterset({'q': 'BFD-SLOW'}, self.queryset).qs.count(), 1)


class PrefixListFilterSetTestCase(FilterSetTestData, FreeTextSearchTests, ChangeLoggedFilterSetTests, TestCase):
    queryset = PrefixList.objects.all()
    filterset = PrefixListFilterSet

    def test_name(self):
        params = {'name': ['PL-CORE-IN']}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_device(self):
        params = {'device_id': [self.devices[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_address_family(self):
        params = {'address_family': [AddressFamilyChoices.FAMILY_IPV6]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_available_on_device(self):
        PrefixList.objects.create(name='PL-SHARED', address_family=AddressFamilyChoices.FAMILY_IPV4)
        # The device's own two lists, plus the shared one.
        params = {'available_on_device': [self.devices[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_shared(self):
        PrefixList.objects.create(name='PL-SHARED', address_family=AddressFamilyChoices.FAMILY_IPV4)
        self.assertEqual(self.filterset({'shared': True}, self.queryset).qs.count(), 1)
        self.assertEqual(self.filterset({'shared': False}, self.queryset).qs.count(), 3)

    def test_search_matches_name(self):
        self.assertEqual(self.filterset({'q': 'CORE-OUT'}, self.queryset).qs.count(), 1)


class PrefixListRuleFilterSetTestCase(FilterSetTestData, FreeTextSearchTests, ChangeLoggedFilterSetTests, TestCase):
    queryset = PrefixListRule.objects.all()
    filterset = PrefixListRuleFilterSet

    def test_prefix_list(self):
        params = {'prefix_list_id': [self.prefix_lists[0].pk]}
        # Two explicit rules plus the signal-created deny-9999 rule.
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)
        params = {'prefix_list': [self.prefix_lists[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_device(self):
        params = {'device_id': [self.devices[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_action(self):
        params = {'action': [ActionChoices.ACTION_PERMIT]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_match_flags(self):
        self.assertEqual(self.filterset({'match_default': True}, self.queryset).qs.count(), 1)
        # One per prefix list, all created by the terminating-rule receiver.
        self.assertEqual(self.filterset({'match_any': True}, self.queryset).qs.count(), 3)

    def test_prefix_lengths(self):
        self.assertEqual(self.filterset({'min_prefix_length': [24]}, self.queryset).qs.count(), 1)
        self.assertEqual(self.filterset({'max_prefix_length': [32]}, self.queryset).qs.count(), 1)

    def test_search_matches_prefix_list_name(self):
        self.assertEqual(self.filterset({'q': 'PL-EDGE-IN'}, self.queryset).qs.count(), 2)


class RouteMapFilterSetTestCase(FilterSetTestData, FreeTextSearchTests, ChangeLoggedFilterSetTests, TestCase):
    queryset = RouteMap.objects.all()
    filterset = RouteMapFilterSet

    def test_name(self):
        params = {'name': ['RM-CORE-IN']}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_device(self):
        params = {'device_id': [self.devices[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_available_on_device(self):
        RouteMap.objects.create(name='RM-SHARED')
        # The device's own two route maps, plus the shared one.
        params = {'available_on_device': [self.devices[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_shared(self):
        RouteMap.objects.create(name='RM-SHARED')
        self.assertEqual(self.filterset({'shared': True}, self.queryset).qs.count(), 1)
        self.assertEqual(self.filterset({'shared': False}, self.queryset).qs.count(), 3)

    def test_search_matches_name(self):
        self.assertEqual(self.filterset({'q': 'RM-EDGE'}, self.queryset).qs.count(), 1)


class RouteMapRuleFilterSetTestCase(FilterSetTestData, FreeTextSearchTests, ChangeLoggedFilterSetTests, TestCase):
    queryset = RouteMapRule.objects.all()
    filterset = RouteMapRuleFilterSet

    def test_route_map(self):
        params = {'route_map_id': [self.route_maps[0].pk]}
        # Two explicit rules plus the signal-created deny-9999 rule.
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)
        params = {'route_map': [self.route_maps[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_device(self):
        params = {'device_id': [self.devices[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_prefix_list(self):
        params = {'prefix_list_id': [self.prefix_lists[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_action(self):
        params = {'action': [ActionChoices.ACTION_DENY]}
        # One explicit deny rule plus one terminating rule per route map.
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 4)

    def test_search_matches_prefix_list_name(self):
        self.assertEqual(self.filterset({'q': 'PL-CORE-IN'}, self.queryset).qs.count(), 1)


#
# BGP
#


class BGPCommunityFilterSetTestCase(FilterSetTestData, FreeTextSearchTests, ChangeLoggedFilterSetTests, TestCase):
    queryset = BGPCommunity.objects.all()
    filterset = BGPCommunityFilterSet

    def test_value(self):
        params = {'value': ['65001:100']}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_type(self):
        params = {'type': [BGPCommunityTypeChoices.TYPE_EXTENDED]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_name(self):
        params = {'name': ['CUSTOMERS']}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_search_matches_value_and_name(self):
        self.assertEqual(self.filterset({'q': 'rt:65001'}, self.queryset).qs.count(), 1)
        self.assertEqual(self.filterset({'q': 'CUSTOMERS'}, self.queryset).qs.count(), 1)


class BGPCommunityListFilterSetTestCase(FilterSetTestData, FreeTextSearchTests, ChangeLoggedFilterSetTests, TestCase):
    queryset = BGPCommunityList.objects.all()
    filterset = BGPCommunityListFilterSet

    def test_name(self):
        params = {'name': ['CL-CORE']}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_device(self):
        params = {'device_id': [self.devices[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_available_on_device(self):
        # The device's own list plus the shared one.
        params = {'available_on_device': [self.devices[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_shared(self):
        self.assertEqual(self.filterset({'shared': True}, self.queryset).qs.count(), 1)
        self.assertEqual(self.filterset({'shared': False}, self.queryset).qs.count(), 2)

    def test_search_matches_name(self):
        self.assertEqual(self.filterset({'q': 'CL-EDGE'}, self.queryset).qs.count(), 1)


class BGPCommunityListRuleFilterSetTestCase(
    FilterSetTestData, FreeTextSearchTests, ChangeLoggedFilterSetTests, TestCase
):
    queryset = BGPCommunityListRule.objects.all()
    filterset = BGPCommunityListRuleFilterSet

    def test_community_list(self):
        params = {'community_list_id': [self.community_lists[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {'community_list': [self.community_lists[2].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_device(self):
        params = {'device_id': [self.devices[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_community(self):
        params = {'community_id': [self.communities[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {'community': [self.communities[1].value]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_action(self):
        params = {'action': [ActionChoices.ACTION_DENY]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_search_matches_list_and_community(self):
        self.assertEqual(self.filterset({'q': 'CL-CORE'}, self.queryset).qs.count(), 2)


class BGPRouterFilterSetTestCase(FilterSetTestData, FreeTextSearchTests, ChangeLoggedFilterSetTests, TestCase):
    queryset = BGPRouter.objects.all()
    filterset = BGPRouterFilterSet

    def test_device(self):
        params = {'device_id': [self.devices[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {'device': [self.devices[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_vrf(self):
        params = {'vrf_id': [self.vrfs[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_asn(self):
        params = {'asn_id': [self.asns[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
        params = {'asn': [self.asns[1].asn]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_booleans(self):
        self.assertEqual(self.filterset({'enable': False}, self.queryset).qs.count(), 1)
        self.assertEqual(self.filterset({'route_reflection': True}, self.queryset).qs.count(), 1)

    def test_search_matches_asn(self):
        self.assertEqual(self.filterset({'q': str(self.asns[0].asn)}, self.queryset).qs.count(), 1)

    def test_search_matches_device_name(self):
        self.assertEqual(self.filterset({'q': 'core-sw2'}, self.queryset).qs.count(), 1)


class BGPPeergroupFilterSetTestCase(
    FilterSetTestData, FreeTextSearchTests, NoPasswordFilterTests, ChangeLoggedFilterSetTests, TestCase
):
    queryset = BGPPeergroup.objects.all()
    filterset = BGPPeergroupFilterSet
    ignore_fields = ('password',)

    def test_bgprouter(self):
        params = {'bgprouter_id': [self.bgp_routers[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_device(self):
        params = {'device_id': [self.devices[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_name(self):
        params = {'name': ['PG-CORE']}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_remote_as(self):
        params = {'remote_as_id': [self.asns[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_bfd(self):
        params = {'bfd_id': [self.bfd_profiles[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
        params = {'bfd': [self.bfd_profiles[0].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_search_matches_name(self):
        self.assertEqual(self.filterset({'q': 'PG-TRANSIT'}, self.queryset).qs.count(), 1)


class BGPPeerFilterSetTestCase(
    FilterSetTestData, FreeTextSearchTests, NoPasswordFilterTests, ChangeLoggedFilterSetTests, TestCase
):
    queryset = BGPPeer.objects.all()
    filterset = BGPPeerFilterSet
    ignore_fields = ('password',)

    def test_bgprouter(self):
        params = {'bgprouter_id': [self.bgp_routers[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_remote_address(self):
        params = {'remote_address_id': [self.addresses4[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_interface(self):
        params = {'interface_id': [self.interfaces1[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_peergroup(self):
        params = {'peergroup_id': [self.peergroups[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
        params = {'peergroup': [self.peergroups[0].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_enable(self):
        self.assertEqual(self.filterset({'enable': False}, self.queryset).qs.count(), 1)

    def test_search_matches_remote_address(self):
        self.assertEqual(self.filterset({'q': '10.123.1.1'}, self.queryset).qs.count(), 1)

    def test_search_matches_interface_name(self):
        self.assertEqual(self.filterset({'q': 'Ethernet1'}, self.queryset).qs.count(), 1)


class BGPAddressFamilyFilterSetTestCase(FilterSetTestData, FreeTextSearchTests, ChangeLoggedFilterSetTests, TestCase):
    queryset = BGPAddressFamily.objects.all()
    filterset = BGPAddressFamilyFilterSet

    # aggregate_routes and networks are both many-to-many to ipam.Prefix, so the
    # audit's default naming (the related model's verbose name) would expect a
    # single `prefix_id` filter to stand for both. Each relation has a filter of
    # its own instead; name them here so the audit checks for both.
    M2M_FILTER_NAMES = {
        'aggregate_routes': 'aggregate_route',
        'networks': 'network',
    }

    def get_m2m_filter_name(self, field):
        if field.name in self.M2M_FILTER_NAMES:
            return self.M2M_FILTER_NAMES[field.name]
        return super().get_m2m_filter_name(field)

    def test_bgprouter(self):
        params = {'bgprouter_id': [self.bgp_routers[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_device(self):
        params = {'device_id': [self.devices[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_family(self):
        params = {'family': [BGPAddressFamilyChoices.AFI_L2VPN_EVPN]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_route_maps(self):
        params = {'network_route_map_id': [self.route_maps[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
        params = {'aggregate_route_map_id': [self.route_maps[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_export_to_evpn(self):
        self.assertEqual(self.filterset({'export_to_evpn': True}, self.queryset).qs.count(), 1)

    def test_aggregate_routes(self):
        params = {'aggregate_route_id': [self.prefixes4[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
        params = {'aggregate_route': [str(self.prefixes4[0].prefix)]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
        # Two prefixes on two different families: one row each.
        params = {'aggregate_route_id': [self.prefixes4[0].pk, self.prefixes6[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        # Two prefixes on the *same* family: still one row, not one per prefix.
        params = {'aggregate_route_id': [self.prefixes4[0].pk, self.prefixes4[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_networks(self):
        # prefixes4[2] is a network statement on both families.
        params = {'network_id': [self.prefixes4[2].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {'network': [str(self.prefixes4[2].prefix)]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {'network_id': [self.prefixes6[1].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_aggregate_routes_and_networks_are_distinct_filters(self):
        # A prefix used only as an aggregate must not match the network filter.
        self.assertEqual(
            self.filterset({'network_id': [self.prefixes4[0].pk]}, self.queryset).qs.count(),
            0,
        )
        # ...and vice versa.
        self.assertEqual(
            self.filterset({'aggregate_route_id': [self.prefixes4[2].pk]}, self.queryset).qs.count(),
            0,
        )

    def test_search_matches_route_map_name(self):
        self.assertEqual(self.filterset({'q': 'RM-CORE-OUT'}, self.queryset).qs.count(), 1)


class BGPAddressFamilyRedistributeFilterSetTestCase(
    FilterSetTestData, FreeTextSearchTests, ChangeLoggedFilterSetTests, TestCase
):
    queryset = BGPAddressFamilyRedistribute.objects.all()
    filterset = BGPAddressFamilyRedistributeFilterSet

    def test_family(self):
        params = {'family_id': [self.address_families[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_bgprouter(self):
        params = {'bgprouter_id': [self.bgp_routers[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_protocol(self):
        params = {'protocol': [BGPRedistributeProtocolChoices.PROTOCOL_STATIC]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_route_map(self):
        params = {'route_map_id': [self.route_maps[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_enable(self):
        self.assertEqual(self.filterset({'enable': False}, self.queryset).qs.count(), 1)

    def test_search_matches_route_map_name(self):
        self.assertEqual(self.filterset({'q': 'RM-CORE-IN'}, self.queryset).qs.count(), 1)


class BGPPeerAddressFamilyFilterSetTestCase(
    FilterSetTestData, FreeTextSearchTests, ChangeLoggedFilterSetTests, TestCase
):
    queryset = BGPPeerAddressFamily.objects.all()
    filterset = BGPPeerAddressFamilyFilterSet

    def test_peer(self):
        params = {'peer_id': [self.peers[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_bgprouter(self):
        params = {'bgprouter_id': [self.bgp_routers[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_family(self):
        params = {'family': [BGPAddressFamilyChoices.AFI_IPV4_UNICAST]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)

    def test_policies(self):
        params = {'inbound_policy_id': [self.route_maps[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_flags(self):
        self.assertEqual(self.filterset({'enable': False}, self.queryset).qs.count(), 1)
        self.assertEqual(self.filterset({'default_originate': True}, self.queryset).qs.count(), 1)

    def test_search_matches_remote_address(self):
        self.assertEqual(self.filterset({'q': '10.123.1.1'}, self.queryset).qs.count(), 2)


class BGPPeergroupAddressFamilyFilterSetTestCase(
    FilterSetTestData, FreeTextSearchTests, ChangeLoggedFilterSetTests, TestCase
):
    queryset = BGPPeergroupAddressFamily.objects.all()
    filterset = BGPPeergroupAddressFamilyFilterSet

    def test_peergroup(self):
        params = {'peergroup_id': [self.peergroups[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 2)
        params = {'peergroup': [self.peergroups[1].name]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_bgprouter(self):
        params = {'bgprouter_id': [self.bgp_routers[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 3)

    def test_family(self):
        params = {'family': [BGPAddressFamilyChoices.AFI_IPV6_UNICAST]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_policies(self):
        params = {'outbound_policy_id': [self.route_maps[0].pk]}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)

    def test_flags(self):
        self.assertEqual(self.filterset({'soft_reconfiguration': False}, self.queryset).qs.count(), 1)
        self.assertEqual(self.filterset({'route_reflector_client': True}, self.queryset).qs.count(), 1)

    def test_search_matches_peergroup_name(self):
        self.assertEqual(self.filterset({'q': 'PG-EDGE'}, self.queryset).qs.count(), 1)
