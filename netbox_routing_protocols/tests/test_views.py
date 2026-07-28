"""
UI view tests.

All twelve models are driven through NetBox's own ``ViewTestCases.PrimaryObjectViewTestCase``,
which is what the core apps use for ``PrimaryModel`` subclasses. That covers detail, changelog,
add, edit, delete, list, export, bulk import, bulk update-by-import, bulk edit and bulk delete,
each with and without permission and under an object-level constraint.

Beyond the generic suites there are two things this module exists to prove:

* ``RuleBulkDeleteWiringTestCase`` — the rule bulk-delete URLs must reach the *rule* views.
  An earlier revision wired ``prefixlistrule_bulk_delete`` to ``PrefixListBulkDeleteView`` (and
  the route-map equivalent), so bulk-deleting rules silently destroyed prefix lists and route
  maps whose primary keys happened to match the submitted rule PKs. The test deliberately
  overlaps the two PK spaces and asserts the parents survive.
* ``ChildObjectTabTestCase`` — every ``ObjectChildrenView`` tab returns 200 and lists that
  parent's children and nobody else's, including the Static Routes tab this plugin attaches to
  the core ``ipam.Prefix`` model.

Two fixture details recur below:

* Creating a ``PrefixList`` or ``RouteMap`` fires a ``post_save`` receiver which adds a
  terminating ``deny 9999 match_any`` rule, so rule counts always include one row per parent
  on top of the rules created explicitly.
* ``BGPPeer``, ``BGPPeergroup`` and ``BGPAddressFamily`` have no ``device``/``vrf`` columns —
  both are properties reached through ``bgprouter`` — so CSV import identifies their parent
  router by the (device, VRF) pair instead.
"""

from django.test import override_settings
from django.urls import reverse

from core.models import ObjectType
from ipam.models import Prefix
from netbox.choices import CSVDelimiterChoices, ImportFormatChoices
from users.models import ObjectPermission
from utilities.testing import TestCase, ViewTestCases

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

# Every model in this plugin lives under the plugins URL namespace, so the base URL format
# NetBox derives from the app label ('<app>:<model>_<action>') needs the 'plugins:' prefix.
URL_NAMESPACE = 'plugins:netbox_routing_protocols'


class RoutingProtocolsViewTestCases:
    """Container so the shared base class is not collected as a test case itself."""

    class PrimaryObjectViewTestCase(BaseTestData, ViewTestCases.PrimaryObjectViewTestCase):
        bulk_edit_data = {
            'description': 'New description',
        }

        def _get_base_url(self):
            return f'{URL_NAMESPACE}:{self.model._meta.model_name}_{{}}'


#
# Static routing
#


class StaticRouteTestCase(RoutingProtocolsViewTestCases.PrimaryObjectViewTestCase):
    model = StaticRoute

    @classmethod
    def setUpTestData(cls):
        cls.build_topology()

        routes = (
            StaticRoute(device=cls.devices[0], vrf=cls.vrfs[0], prefix=cls.prefixes4[0], nexthop=cls.addresses4[0]),
            StaticRoute(device=cls.devices[0], vrf=cls.vrfs[0], prefix=cls.prefixes4[1], nexthop=cls.addresses4[1]),
            StaticRoute(device=cls.devices[0], vrf=cls.vrfs[0], prefix=cls.prefixes4[2], nexthop=cls.addresses4[2]),
        )
        for route in routes:
            route.save()

        cls.form_data = {
            'device': cls.devices[1].pk,
            'vrf': cls.vrfs[0].pk,
            'prefix': cls.prefixes4[7].pk,
            'nexthop': cls.addresses4[7].pk,
            'default_route': False,
            'description': 'Created via the UI',
            'comments': 'Some comments',
        }

        cls.csv_data = (
            'device,vrf,prefix,nexthop,description',
            f'{cls.devices[1].name},{cls.vrfs[0].name},{cls.prefixes4[3].prefix},{cls.addresses4[3].address},Route 1',
            f'{cls.devices[1].name},{cls.vrfs[0].name},{cls.prefixes4[4].prefix},{cls.addresses4[4].address},Route 2',
            f'{cls.devices[1].name},{cls.vrfs[0].name},{cls.prefixes4[5].prefix},{cls.addresses4[5].address},Route 3',
        )

        cls.csv_update_data = (
            'id,description',
            f'{routes[0].pk},Updated description 1',
            f'{routes[1].pk},Updated description 2',
            f'{routes[2].pk},Updated description 3',
        )


#
# Routing policy
#


class PrefixListTestCase(RoutingProtocolsViewTestCases.PrimaryObjectViewTestCase):
    model = PrefixList

    @classmethod
    def setUpTestData(cls):
        cls.build_topology()

        # Each of these also gains a terminating deny-9999 rule from the post_save receiver.
        prefix_lists = [
            PrefixList.objects.create(
                name=name,
                device=cls.devices[0],
                address_family=AddressFamilyChoices.FAMILY_IPV4,
            )
            for name in ('PL-CORE-IN', 'PL-CORE-OUT', 'PL-EDGE-IN')
        ]

        cls.form_data = {
            'name': 'PL-NEW',
            'device': cls.devices[1].pk,
            'address_family': AddressFamilyChoices.FAMILY_IPV4,
            'description': 'Created via the UI',
            'comments': 'Some comments',
        }

        cls.csv_data = (
            'device,name,address_family,description',
            f'{cls.devices[1].name},PL-CSV-1,{AddressFamilyChoices.FAMILY_IPV4},List 1',
            f'{cls.devices[1].name},PL-CSV-2,{AddressFamilyChoices.FAMILY_IPV6},List 2',
            f'{cls.devices[1].name},PL-CSV-3,{AddressFamilyChoices.FAMILY_IPV4},List 3',
        )

        cls.csv_update_data = (
            'id,description',
            f'{prefix_lists[0].pk},Updated description 1',
            f'{prefix_lists[1].pk},Updated description 2',
            f'{prefix_lists[2].pk},Updated description 3',
        )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=['*'], EXEMPT_EXCLUDE_MODELS=[])
    def test_bulk_import_also_creates_the_terminating_rule(self):
        """Every prefix list created by import gets its deny-9999 rule, just like one created by hand."""
        self.add_permissions('netbox_routing_protocols.add_prefixlist')
        initial_rules = PrefixListRule.objects.count()

        response = self.client.post(
            self._get_url('bulk_import'),
            {
                'data': '\n'.join(self.csv_data),
                'format': ImportFormatChoices.CSV,
                'csv_delimiter': CSVDelimiterChoices.AUTO,
            },
        )
        self.assertHttpStatus(response, 302)

        # Three lists imported, so three more terminating rules.
        self.assertEqual(PrefixListRule.objects.count(), initial_rules + 3)


class PrefixListRuleTestCase(RoutingProtocolsViewTestCases.PrimaryObjectViewTestCase):
    model = PrefixListRule

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

        rules = [
            PrefixListRule.objects.create(
                prefix_list=cls.prefix_list,
                sequence=sequence,
                action=ActionChoices.ACTION_PERMIT,
                prefix=prefix,
            )
            for sequence, prefix in ((10, cls.prefixes4[0]), (20, cls.prefixes4[1]), (30, cls.prefixes4[2]))
        ]

        cls.form_data = {
            'prefix_list': cls.other_prefix_list.pk,
            'sequence': 100,
            'action': ActionChoices.ACTION_PERMIT,
            'prefix': cls.prefixes4[3].pk,
            'min_prefix_length': 24,
            'max_prefix_length': 32,
            'match_any': False,
            'match_default': False,
            'description': 'Created via the UI',
            'comments': 'Some comments',
        }

        cls.csv_data = (
            'device,prefix_list,sequence,action,prefix,description',
            f'{cls.devices[0].name},{cls.other_prefix_list.name},110,'
            f'{ActionChoices.ACTION_PERMIT},{cls.prefixes4[4].prefix},Rule 1',
            f'{cls.devices[0].name},{cls.other_prefix_list.name},120,'
            f'{ActionChoices.ACTION_PERMIT},{cls.prefixes4[5].prefix},Rule 2',
            f'{cls.devices[0].name},{cls.other_prefix_list.name},130,'
            f'{ActionChoices.ACTION_DENY},{cls.prefixes4[6].prefix},Rule 3',
        )

        cls.csv_update_data = (
            'id,description',
            f'{rules[0].pk},Updated description 1',
            f'{rules[1].pk},Updated description 2',
            f'{rules[2].pk},Updated description 3',
        )


class RouteMapTestCase(RoutingProtocolsViewTestCases.PrimaryObjectViewTestCase):
    model = RouteMap

    @classmethod
    def setUpTestData(cls):
        cls.build_topology()

        route_maps = [RouteMap.objects.create(name=name, device=cls.devices[0]) for name in ('RM-1', 'RM-2', 'RM-3')]

        cls.form_data = {
            'name': 'RM-NEW',
            'device': cls.devices[1].pk,
            'description': 'Created via the UI',
            'comments': 'Some comments',
        }

        cls.csv_data = (
            'device,name,description',
            f'{cls.devices[1].name},RM-CSV-1,Map 1',
            f'{cls.devices[1].name},RM-CSV-2,Map 2',
            f'{cls.devices[1].name},RM-CSV-3,Map 3',
        )

        cls.csv_update_data = (
            'id,description',
            f'{route_maps[0].pk},Updated description 1',
            f'{route_maps[1].pk},Updated description 2',
            f'{route_maps[2].pk},Updated description 3',
        )


class RouteMapRuleTestCase(RoutingProtocolsViewTestCases.PrimaryObjectViewTestCase):
    model = RouteMapRule

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

        rules = [
            RouteMapRule.objects.create(
                route_map=cls.route_map,
                sequence=sequence,
                action=ActionChoices.ACTION_PERMIT,
                prefix_list=prefix_list,
            )
            for sequence, prefix_list in (
                (10, cls.prefix_lists[0]),
                (20, cls.prefix_lists[1]),
                (30, cls.prefix_lists[2]),
            )
        ]

        cls.form_data = {
            'route_map': cls.other_route_map.pk,
            'sequence': 100,
            'action': ActionChoices.ACTION_PERMIT,
            'prefix_list': cls.prefix_lists[0].pk,
            'match_any': False,
            'description': 'Created via the UI',
            'comments': 'Some comments',
        }

        cls.csv_data = (
            'device,route_map,sequence,action,prefix_list,description',
            f'{cls.devices[0].name},{cls.other_route_map.name},110,'
            f'{ActionChoices.ACTION_PERMIT},{cls.prefix_lists[0].name},Rule 1',
            f'{cls.devices[0].name},{cls.other_route_map.name},120,'
            f'{ActionChoices.ACTION_PERMIT},{cls.prefix_lists[1].name},Rule 2',
            f'{cls.devices[0].name},{cls.other_route_map.name},130,'
            f'{ActionChoices.ACTION_DENY},{cls.prefix_lists[2].name},Rule 3',
        )

        cls.csv_update_data = (
            'id,description',
            f'{rules[0].pk},Updated description 1',
            f'{rules[1].pk},Updated description 2',
            f'{rules[2].pk},Updated description 3',
        )


#
# BGP
#


class BGPRouterTestCase(RoutingProtocolsViewTestCases.PrimaryObjectViewTestCase):
    model = BGPRouter

    @classmethod
    def setUpTestData(cls):
        cls.build_topology()

        routers = [BGPRouter.objects.create(device=cls.devices[0], vrf=vrf, asn=cls.asns[0]) for vrf in cls.vrfs]

        cls.form_data = {
            'device': cls.devices[1].pk,
            'vrf': cls.vrfs[0].pk,
            'asn': cls.asns[1].pk,
            'enable': True,
            'aspath_ignore': True,
            'route_reflection': True,
            'enable_evpn': False,
            'description': 'Created via the UI',
            'comments': 'Some comments',
        }

        cls.csv_data = (
            'device,vrf,asn,description',
            f'{cls.devices[1].name},{cls.vrfs[0].name},{cls.asns[1].asn},Router 1',
            f'{cls.devices[1].name},{cls.vrfs[1].name},{cls.asns[2].asn},Router 2',
            f'{cls.devices[1].name},{cls.vrfs[2].name},{cls.asns[3].asn},Router 3',
        )

        cls.csv_update_data = (
            'id,description',
            f'{routers[0].pk},Updated description 1',
            f'{routers[1].pk},Updated description 2',
            f'{routers[2].pk},Updated description 3',
        )


class BGPPeergroupTestCase(RoutingProtocolsViewTestCases.PrimaryObjectViewTestCase):
    model = BGPPeergroup

    @classmethod
    def setUpTestData(cls):
        cls.build_topology()

        cls.router = BGPRouter.objects.create(device=cls.devices[0], vrf=cls.vrfs[0])
        cls.other_router = BGPRouter.objects.create(device=cls.devices[1], vrf=cls.vrfs[0])

        peergroups = [
            BGPPeergroup.objects.create(bgprouter=cls.router, name=name, remote_as=cls.asns[0])
            for name in ('PG-CORE', 'PG-EDGE', 'PG-TRANSIT')
        ]

        cls.form_data = {
            'bgprouter': cls.other_router.pk,
            'name': 'PG-NEW',
            'enable': True,
            'remote_as': cls.asns[1].pk,
            'bfd': True,
            'ebgp_multihop': False,
            'description': 'Created via the UI',
            'comments': 'Some comments',
        }

        # BGPPeergroup has no device/vrf column: the parent router is resolved from the pair.
        cls.csv_data = (
            'device,vrf,name,remote_as,description',
            f'{cls.devices[1].name},{cls.vrfs[0].name},PG-CSV-1,{cls.asns[1].asn},Group 1',
            f'{cls.devices[1].name},{cls.vrfs[0].name},PG-CSV-2,{cls.asns[2].asn},Group 2',
            f'{cls.devices[1].name},{cls.vrfs[0].name},PG-CSV-3,{cls.asns[3].asn},Group 3',
        )

        cls.csv_update_data = (
            'id,description',
            f'{peergroups[0].pk},Updated description 1',
            f'{peergroups[1].pk},Updated description 2',
            f'{peergroups[2].pk},Updated description 3',
        )


class BGPPeerTestCase(RoutingProtocolsViewTestCases.PrimaryObjectViewTestCase):
    model = BGPPeer

    @classmethod
    def setUpTestData(cls):
        cls.build_topology()

        cls.router = BGPRouter.objects.create(device=cls.devices[0], vrf=cls.vrfs[0])
        cls.other_router = BGPRouter.objects.create(device=cls.devices[1], vrf=cls.vrfs[0])

        peers = [
            BGPPeer.objects.create(bgprouter=cls.router, remote_address=address, remote_as=cls.asns[0])
            for address in (cls.addresses4[0], cls.addresses4[1], cls.addresses4[2])
        ]

        cls.form_data = {
            'bgprouter': cls.other_router.pk,
            'remote_address': cls.addresses4[7].pk,
            'remote_as': cls.asns[1].pk,
            'enable': True,
            'bfd': True,
            'ebgp_multihop': False,
            'description': 'Created via the UI',
            'comments': 'Some comments',
        }

        # BGPPeer has no device/vrf column: the parent router is resolved from the pair.
        cls.csv_data = (
            'device,vrf,remote_address,remote_as,description',
            f'{cls.devices[1].name},{cls.vrfs[0].name},{cls.addresses4[3].address},{cls.asns[1].asn},Peer 1',
            f'{cls.devices[1].name},{cls.vrfs[0].name},{cls.addresses4[4].address},{cls.asns[2].asn},Peer 2',
            f'{cls.devices[1].name},{cls.vrfs[0].name},{cls.addresses4[5].address},{cls.asns[3].asn},Peer 3',
        )

        cls.csv_update_data = (
            'id,description',
            f'{peers[0].pk},Updated description 1',
            f'{peers[1].pk},Updated description 2',
            f'{peers[2].pk},Updated description 3',
        )


class BGPAddressFamilyTestCase(RoutingProtocolsViewTestCases.PrimaryObjectViewTestCase):
    model = BGPAddressFamily

    @classmethod
    def setUpTestData(cls):
        cls.build_topology()

        cls.router = BGPRouter.objects.create(device=cls.devices[0], vrf=cls.vrfs[0])
        cls.other_router = BGPRouter.objects.create(device=cls.devices[1], vrf=cls.vrfs[0])
        cls.route_map = RouteMap.objects.create(name='RM-1', device=cls.devices[1])

        families = [
            BGPAddressFamily.objects.create(bgprouter=cls.router, family=family)
            for family in (
                BGPAddressFamilyChoices.AFI_IPV4_UNICAST,
                BGPAddressFamilyChoices.AFI_IPV6_UNICAST,
                BGPAddressFamilyChoices.AFI_L2VPN_EVPN,
            )
        ]

        cls.form_data = {
            'bgprouter': cls.other_router.pk,
            'family': BGPAddressFamilyChoices.AFI_IPV4_UNICAST,
            'enable': True,
            'aggregate_routes': sorted([cls.prefixes4[0].pk]),
            'networks': sorted([cls.prefixes4[1].pk, cls.prefixes4[2].pk]),
            'network_route_map': cls.route_map.pk,
            'export_to_evpn': False,
            'description': 'Created via the UI',
            'comments': 'Some comments',
        }

        # BGPAddressFamily has no device/vrf column: the parent router is resolved from the pair.
        cls.csv_data = (
            'device,vrf,family,description',
            f'{cls.devices[1].name},{cls.vrfs[0].name},{BGPAddressFamilyChoices.AFI_IPV4_UNICAST},Family 1',
            f'{cls.devices[1].name},{cls.vrfs[0].name},{BGPAddressFamilyChoices.AFI_IPV6_UNICAST},Family 2',
            f'{cls.devices[1].name},{cls.vrfs[0].name},{BGPAddressFamilyChoices.AFI_L2VPN_EVPN},Family 3',
        )

        cls.csv_update_data = (
            'id,description',
            f'{families[0].pk},Updated description 1',
            f'{families[1].pk},Updated description 2',
            f'{families[2].pk},Updated description 3',
        )


class BGPAddressFamilyRedistributeTestCase(RoutingProtocolsViewTestCases.PrimaryObjectViewTestCase):
    model = BGPAddressFamilyRedistribute

    @classmethod
    def setUpTestData(cls):
        cls.build_topology()

        cls.router = BGPRouter.objects.create(device=cls.devices[0], vrf=cls.vrfs[0])
        cls.families = [
            BGPAddressFamily.objects.create(bgprouter=cls.router, family=family)
            for family in (
                BGPAddressFamilyChoices.AFI_IPV4_UNICAST,
                BGPAddressFamilyChoices.AFI_IPV6_UNICAST,
                BGPAddressFamilyChoices.AFI_L2VPN_EVPN,
            )
        ]
        cls.route_map = RouteMap.objects.create(name='RM-1', device=cls.devices[0])

        # Only two source protocols exist, and (family, protocol) is unique, so three objects
        # means spreading them across two families.
        redistributions = [
            BGPAddressFamilyRedistribute.objects.create(
                family=cls.families[0], protocol=BGPRedistributeProtocolChoices.PROTOCOL_CONNECTED
            ),
            BGPAddressFamilyRedistribute.objects.create(
                family=cls.families[0], protocol=BGPRedistributeProtocolChoices.PROTOCOL_STATIC
            ),
            BGPAddressFamilyRedistribute.objects.create(
                family=cls.families[1], protocol=BGPRedistributeProtocolChoices.PROTOCOL_CONNECTED
            ),
        ]

        cls.form_data = {
            'family': cls.families[2].pk,
            'protocol': BGPRedistributeProtocolChoices.PROTOCOL_STATIC,
            'enable': True,
            'route_map': cls.route_map.pk,
            'description': 'Created via the UI',
            'comments': 'Some comments',
        }

        cls.csv_data = (
            'device,vrf,family,protocol,description',
            f'{cls.devices[0].name},{cls.vrfs[0].name},{BGPAddressFamilyChoices.AFI_IPV6_UNICAST},'
            f'{BGPRedistributeProtocolChoices.PROTOCOL_STATIC},Redistribution 1',
            f'{cls.devices[0].name},{cls.vrfs[0].name},{BGPAddressFamilyChoices.AFI_L2VPN_EVPN},'
            f'{BGPRedistributeProtocolChoices.PROTOCOL_CONNECTED},Redistribution 2',
            f'{cls.devices[0].name},{cls.vrfs[0].name},{BGPAddressFamilyChoices.AFI_L2VPN_EVPN},'
            f'{BGPRedistributeProtocolChoices.PROTOCOL_STATIC},Redistribution 3',
        )

        cls.csv_update_data = (
            'id,description',
            f'{redistributions[0].pk},Updated description 1',
            f'{redistributions[1].pk},Updated description 2',
            f'{redistributions[2].pk},Updated description 3',
        )


class BGPPeerAddressFamilyTestCase(RoutingProtocolsViewTestCases.PrimaryObjectViewTestCase):
    model = BGPPeerAddressFamily

    @classmethod
    def setUpTestData(cls):
        cls.build_topology()

        cls.router = BGPRouter.objects.create(device=cls.devices[0], vrf=cls.vrfs[0])
        cls.peer = BGPPeer.objects.create(bgprouter=cls.router, remote_address=cls.addresses4[0], remote_as=cls.asns[0])
        cls.other_peer = BGPPeer.objects.create(
            bgprouter=cls.router, remote_address=cls.addresses4[1], remote_as=cls.asns[0]
        )
        cls.route_map = RouteMap.objects.create(name='RM-1', device=cls.devices[0])

        peer_families = [
            BGPPeerAddressFamily.objects.create(peer=cls.peer, family=family)
            for family in (
                BGPAddressFamilyChoices.AFI_IPV4_UNICAST,
                BGPAddressFamilyChoices.AFI_IPV6_UNICAST,
                BGPAddressFamilyChoices.AFI_L2VPN_EVPN,
            )
        ]

        cls.form_data = {
            'peer': cls.other_peer.pk,
            'family': BGPAddressFamilyChoices.AFI_IPV4_UNICAST,
            'enable': True,
            'inbound_policy': cls.route_map.pk,
            'outbound_policy': cls.route_map.pk,
            'soft_reconfiguration': True,
            'default_originate': False,
            'route_reflector_client': False,
            'description': 'Created via the UI',
            'comments': 'Some comments',
        }

        cls.csv_data = (
            'device,vrf,peer,family,description',
            f'{cls.devices[0].name},{cls.vrfs[0].name},{cls.other_peer.remote_address.address},'
            f'{BGPAddressFamilyChoices.AFI_IPV4_UNICAST},Peer family 1',
            f'{cls.devices[0].name},{cls.vrfs[0].name},{cls.other_peer.remote_address.address},'
            f'{BGPAddressFamilyChoices.AFI_IPV6_UNICAST},Peer family 2',
            f'{cls.devices[0].name},{cls.vrfs[0].name},{cls.other_peer.remote_address.address},'
            f'{BGPAddressFamilyChoices.AFI_L2VPN_EVPN},Peer family 3',
        )

        cls.csv_update_data = (
            'id,description',
            f'{peer_families[0].pk},Updated description 1',
            f'{peer_families[1].pk},Updated description 2',
            f'{peer_families[2].pk},Updated description 3',
        )


class BGPPeergroupAddressFamilyTestCase(RoutingProtocolsViewTestCases.PrimaryObjectViewTestCase):
    model = BGPPeergroupAddressFamily

    @classmethod
    def setUpTestData(cls):
        cls.build_topology()

        cls.router = BGPRouter.objects.create(device=cls.devices[0], vrf=cls.vrfs[0])
        cls.peergroup = BGPPeergroup.objects.create(bgprouter=cls.router, name='PG-CORE', remote_as=cls.asns[0])
        cls.other_peergroup = BGPPeergroup.objects.create(bgprouter=cls.router, name='PG-EDGE', remote_as=cls.asns[0])
        cls.route_map = RouteMap.objects.create(name='RM-1', device=cls.devices[0])

        peergroup_families = [
            BGPPeergroupAddressFamily.objects.create(peergroup=cls.peergroup, family=family)
            for family in (
                BGPAddressFamilyChoices.AFI_IPV4_UNICAST,
                BGPAddressFamilyChoices.AFI_IPV6_UNICAST,
                BGPAddressFamilyChoices.AFI_L2VPN_EVPN,
            )
        ]

        cls.form_data = {
            'peergroup': cls.other_peergroup.pk,
            'family': BGPAddressFamilyChoices.AFI_IPV4_UNICAST,
            'enable': True,
            'inbound_policy': cls.route_map.pk,
            'outbound_policy': cls.route_map.pk,
            'soft_reconfiguration': True,
            'default_originate': False,
            'route_reflector_client': False,
            'description': 'Created via the UI',
            'comments': 'Some comments',
        }

        cls.csv_data = (
            'device,vrf,peergroup,family,description',
            f'{cls.devices[0].name},{cls.vrfs[0].name},{cls.other_peergroup.name},'
            f'{BGPAddressFamilyChoices.AFI_IPV4_UNICAST},Group family 1',
            f'{cls.devices[0].name},{cls.vrfs[0].name},{cls.other_peergroup.name},'
            f'{BGPAddressFamilyChoices.AFI_IPV6_UNICAST},Group family 2',
            f'{cls.devices[0].name},{cls.vrfs[0].name},{cls.other_peergroup.name},'
            f'{BGPAddressFamilyChoices.AFI_L2VPN_EVPN},Group family 3',
        )

        cls.csv_update_data = (
            'id,description',
            f'{peergroup_families[0].pk},Updated description 1',
            f'{peergroup_families[1].pk},Updated description 2',
            f'{peergroup_families[2].pk},Updated description 3',
        )


#
# Regression: rule bulk-delete URL wiring
#


class RuleBulkDeleteWiringTestCase(BaseTestData, TestCase):
    """
    Bulk-deleting rules must delete rules, and nothing else.

    A previous revision hand-wrote the URL table and pointed `prefixlistrule_bulk_delete` at
    `PrefixListBulkDeleteView` (and `routemaprule_bulk_delete` at `RouteMapBulkDeleteView`).
    Because a bulk-delete view resolves the submitted PKs against its *own* queryset, posting
    rule PKs to the parent's view deleted the prefix lists and route maps that happened to
    carry those PKs, cascading their rules with them.

    Each test below forces the two PK spaces to overlap by assigning explicit primary keys,
    grants delete permission on both the child *and* the parent (so a mis-wired URL would
    genuinely destroy the parent rather than merely 403), then asserts every parent survives.
    """

    # Explicit primary keys, well clear of the sequences, so the rule PKs submitted for
    # deletion are also valid PKs in the parent table.
    PK_BASE = 900000

    def _grant_delete(self, *models):
        obj_perm = ObjectPermission(name='Test permission', actions=['view', 'delete'])
        obj_perm.save()
        obj_perm.users.add(self.user)
        for model in models:
            obj_perm.object_types.add(ObjectType.objects.get_for_model(model))

    def _bulk_delete(self, url_name, pk_list):
        return self.client.post(
            reverse(f'{URL_NAMESPACE}:{url_name}'),
            {'pk': pk_list, 'confirm': True, '_confirm': True},
        )

    def test_prefix_list_rule_bulk_delete_does_not_touch_prefix_lists(self):
        self.build_topology()

        prefix_lists = [
            PrefixList.objects.create(
                pk=self.PK_BASE + i,
                name=f'PL-{i}',
                device=self.devices[0],
                address_family=AddressFamilyChoices.FAMILY_IPV4,
            )
            for i in range(5)
        ]
        rules = [
            PrefixListRule.objects.create(
                pk=self.PK_BASE + i,
                prefix_list=prefix_lists[0],
                sequence=10 + i,
                action=ActionChoices.ACTION_PERMIT,
                prefix=self.prefixes4[i],
            )
            for i in range(3)
        ]

        list_pks = {obj.pk for obj in prefix_lists}
        rule_pks = [rule.pk for rule in rules]
        # The whole point: every PK about to be deleted is also a live PrefixList PK.
        self.assertTrue(set(rule_pks).issubset(list_pks))

        self._grant_delete(PrefixListRule, PrefixList)
        response = self._bulk_delete('prefixlistrule_bulk_delete', rule_pks)
        self.assertHttpStatus(response, 302)

        # The selected rules are gone...
        self.assertFalse(PrefixListRule.objects.filter(pk__in=rule_pks).exists())
        # ...and every prefix list survives, including those sharing a PK with a deleted rule.
        self.assertEqual(PrefixList.objects.filter(pk__in=list_pks).count(), len(prefix_lists))
        # The terminating deny-9999 rule of each list is untouched as well.
        self.assertEqual(PrefixListRule.objects.filter(prefix_list__in=prefix_lists).count(), len(prefix_lists))

    def test_route_map_rule_bulk_delete_does_not_touch_route_maps(self):
        self.build_topology()

        route_maps = [
            RouteMap.objects.create(pk=self.PK_BASE + i, name=f'RM-{i}', device=self.devices[0]) for i in range(5)
        ]
        prefix_lists = [
            PrefixList.objects.create(
                name=f'PL-{i}',
                device=self.devices[0],
                address_family=AddressFamilyChoices.FAMILY_IPV4,
            )
            for i in range(3)
        ]
        rules = [
            RouteMapRule.objects.create(
                pk=self.PK_BASE + i,
                route_map=route_maps[0],
                sequence=10 + i,
                action=ActionChoices.ACTION_PERMIT,
                prefix_list=prefix_lists[i],
            )
            for i in range(3)
        ]

        map_pks = {obj.pk for obj in route_maps}
        rule_pks = [rule.pk for rule in rules]
        self.assertTrue(set(rule_pks).issubset(map_pks))

        self._grant_delete(RouteMapRule, RouteMap)
        response = self._bulk_delete('routemaprule_bulk_delete', rule_pks)
        self.assertHttpStatus(response, 302)

        self.assertFalse(RouteMapRule.objects.filter(pk__in=rule_pks).exists())
        self.assertEqual(RouteMap.objects.filter(pk__in=map_pks).count(), len(route_maps))
        self.assertEqual(RouteMapRule.objects.filter(route_map__in=route_maps).count(), len(route_maps))

    def test_prefix_list_bulk_delete_still_deletes_prefix_lists(self):
        """The mirror image: the parent's own bulk-delete URL must still work."""
        self.build_topology()

        prefix_lists = [
            PrefixList.objects.create(
                name=f'PL-{i}',
                device=self.devices[0],
                address_family=AddressFamilyChoices.FAMILY_IPV4,
            )
            for i in range(3)
        ]

        self._grant_delete(PrefixList, PrefixListRule)
        pk_list = [obj.pk for obj in prefix_lists[:2]]
        response = self._bulk_delete('prefixlist_bulk_delete', pk_list)
        self.assertHttpStatus(response, 302)

        self.assertFalse(PrefixList.objects.filter(pk__in=pk_list).exists())
        self.assertTrue(PrefixList.objects.filter(pk=prefix_lists[2].pk).exists())

    def test_route_map_bulk_delete_still_deletes_route_maps(self):
        self.build_topology()

        route_maps = [RouteMap.objects.create(name=f'RM-{i}', device=self.devices[0]) for i in range(3)]

        self._grant_delete(RouteMap, RouteMapRule)
        pk_list = [obj.pk for obj in route_maps[:2]]
        response = self._bulk_delete('routemap_bulk_delete', pk_list)
        self.assertHttpStatus(response, 302)

        self.assertFalse(RouteMap.objects.filter(pk__in=pk_list).exists())
        self.assertTrue(RouteMap.objects.filter(pk=route_maps[2].pk).exists())


#
# Child object tabs
#


@override_settings(EXEMPT_VIEW_PERMISSIONS=['*'])
class ChildObjectTabTestCase(BaseTestData, TestCase):
    """
    Every `ObjectChildrenView` tab renders, and shows only its own parent's children.

    The Static Routes tab is included even though it hangs off `ipam.Prefix`, a core model:
    a plugin tab registered against another app's model is the case most likely to break
    silently on upgrade.
    """

    @classmethod
    def setUpTestData(cls):
        cls.build_topology()

        # Routing policy
        cls.prefix_lists = [
            PrefixList.objects.create(name=name, device=cls.devices[0], address_family=AddressFamilyChoices.FAMILY_IPV4)
            for name in ('PL-A', 'PL-B')
        ]
        cls.prefix_list_rules = [
            PrefixListRule.objects.create(
                prefix_list=cls.prefix_lists[0],
                sequence=10,
                action=ActionChoices.ACTION_PERMIT,
                prefix=cls.prefixes4[0],
            ),
            PrefixListRule.objects.create(
                prefix_list=cls.prefix_lists[1],
                sequence=10,
                action=ActionChoices.ACTION_PERMIT,
                prefix=cls.prefixes4[1],
            ),
        ]

        cls.route_maps = [RouteMap.objects.create(name=name, device=cls.devices[0]) for name in ('RM-A', 'RM-B')]
        cls.route_map_rules = [
            RouteMapRule.objects.create(
                route_map=cls.route_maps[0],
                sequence=10,
                action=ActionChoices.ACTION_PERMIT,
                prefix_list=cls.prefix_lists[0],
            ),
            RouteMapRule.objects.create(
                route_map=cls.route_maps[1],
                sequence=10,
                action=ActionChoices.ACTION_PERMIT,
                prefix_list=cls.prefix_lists[1],
            ),
        ]

        # BGP
        cls.routers = [
            BGPRouter.objects.create(device=cls.devices[0], vrf=cls.vrfs[0]),
            BGPRouter.objects.create(device=cls.devices[1], vrf=cls.vrfs[0]),
        ]
        cls.address_families = [
            BGPAddressFamily.objects.create(bgprouter=router, family=BGPAddressFamilyChoices.AFI_IPV4_UNICAST)
            for router in cls.routers
        ]
        cls.redistributions = [
            BGPAddressFamilyRedistribute.objects.create(
                family=family, protocol=BGPRedistributeProtocolChoices.PROTOCOL_CONNECTED
            )
            for family in cls.address_families
        ]
        cls.peergroups = [
            BGPPeergroup.objects.create(bgprouter=router, name=f'PG-{i}', remote_as=cls.asns[0])
            for i, router in enumerate(cls.routers)
        ]
        cls.peers = [
            BGPPeer.objects.create(
                bgprouter=cls.routers[0],
                remote_address=cls.addresses4[0],
                remote_as=cls.asns[0],
                peergroup=cls.peergroups[0],
            ),
            BGPPeer.objects.create(
                bgprouter=cls.routers[1],
                remote_address=cls.addresses4[1],
                remote_as=cls.asns[0],
                peergroup=cls.peergroups[1],
            ),
        ]
        cls.peer_families = [
            BGPPeerAddressFamily.objects.create(peer=peer, family=BGPAddressFamilyChoices.AFI_IPV4_UNICAST)
            for peer in cls.peers
        ]
        cls.peergroup_families = [
            BGPPeergroupAddressFamily.objects.create(
                peergroup=peergroup, family=BGPAddressFamilyChoices.AFI_IPV4_UNICAST
            )
            for peergroup in cls.peergroups
        ]

        # Static routes, hung off two different core prefixes.
        cls.static_routes = [
            StaticRoute.objects.create(
                device=cls.devices[0], vrf=cls.vrfs[0], prefix=cls.prefixes4[0], nexthop=cls.addresses4[0]
            ),
            StaticRoute.objects.create(
                device=cls.devices[0], vrf=cls.vrfs[0], prefix=cls.prefixes4[1], nexthop=cls.addresses4[1]
            ),
        ]

    def assertTabListsOnly(self, url, expected, unexpected):
        """GET a tab URL and assert it lists `expected` and not `unexpected`."""
        response = self.client.get(url)
        self.assertHttpStatus(response, 200)
        content = response.content.decode()
        self.assertIn(expected.get_absolute_url(), content)
        self.assertNotIn(unexpected.get_absolute_url(), content)

    def test_prefix_list_rules_tab(self):
        url = reverse(f'{URL_NAMESPACE}:prefixlist_rules', kwargs={'pk': self.prefix_lists[0].pk})
        self.assertTabListsOnly(url, self.prefix_list_rules[0], self.prefix_list_rules[1])

    def test_route_map_rules_tab(self):
        url = reverse(f'{URL_NAMESPACE}:routemap_rules', kwargs={'pk': self.route_maps[0].pk})
        self.assertTabListsOnly(url, self.route_map_rules[0], self.route_map_rules[1])

    def test_bgp_router_address_families_tab(self):
        url = reverse(f'{URL_NAMESPACE}:bgprouter_address-families', kwargs={'pk': self.routers[0].pk})
        self.assertTabListsOnly(url, self.address_families[0], self.address_families[1])

    def test_bgp_router_peers_tab(self):
        url = reverse(f'{URL_NAMESPACE}:bgprouter_peers', kwargs={'pk': self.routers[0].pk})
        self.assertTabListsOnly(url, self.peers[0], self.peers[1])

    def test_bgp_router_peer_groups_tab(self):
        url = reverse(f'{URL_NAMESPACE}:bgprouter_peer-groups', kwargs={'pk': self.routers[0].pk})
        self.assertTabListsOnly(url, self.peergroups[0], self.peergroups[1])

    def test_bgp_peergroup_address_families_tab(self):
        url = reverse(f'{URL_NAMESPACE}:bgppeergroup_address-families', kwargs={'pk': self.peergroups[0].pk})
        self.assertTabListsOnly(url, self.peergroup_families[0], self.peergroup_families[1])

    def test_bgp_peergroup_peers_tab(self):
        url = reverse(f'{URL_NAMESPACE}:bgppeergroup_peers', kwargs={'pk': self.peergroups[0].pk})
        self.assertTabListsOnly(url, self.peers[0], self.peers[1])

    def test_bgp_peer_address_families_tab(self):
        url = reverse(f'{URL_NAMESPACE}:bgppeer_address-families', kwargs={'pk': self.peers[0].pk})
        self.assertTabListsOnly(url, self.peer_families[0], self.peer_families[1])

    def test_bgp_address_family_redistributions_tab(self):
        url = reverse(f'{URL_NAMESPACE}:bgpaddressfamily_redistributions', kwargs={'pk': self.address_families[0].pk})
        self.assertTabListsOnly(url, self.redistributions[0], self.redistributions[1])

    def test_prefix_static_routes_tab(self):
        """The one tab this plugin attaches to a core model."""
        url = reverse('ipam:prefix_static-routes', kwargs={'pk': self.prefixes4[0].pk})
        self.assertTabListsOnly(url, self.static_routes[0], self.static_routes[1])

    def test_prefix_static_routes_tab_is_empty_for_an_unused_prefix(self):
        url = reverse('ipam:prefix_static-routes', kwargs={'pk': self.prefixes4[7].pk})
        response = self.client.get(url)
        self.assertHttpStatus(response, 200)
        content = response.content.decode()
        for route in self.static_routes:
            self.assertNotIn(route.get_absolute_url(), content)

    # The class-level exemption would bypass the very constraint under test here.
    @override_settings(EXEMPT_VIEW_PERMISSIONS=[])
    def test_child_tabs_respect_object_permissions(self):
        """A tab lists only children the user is permitted to see."""
        # The parent object itself must remain visible for the tab to render at all.
        self.add_permissions('netbox_routing_protocols.view_prefixlist')

        obj_perm = ObjectPermission(
            name='Constrained rules',
            actions=['view'],
            constraints={'pk': self.prefix_list_rules[0].pk},
        )
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ObjectType.objects.get_for_model(PrefixListRule))

        url = reverse(f'{URL_NAMESPACE}:prefixlist_rules', kwargs={'pk': self.prefix_lists[0].pk})
        response = self.client.get(url)
        self.assertHttpStatus(response, 200)
        content = response.content.decode()
        self.assertIn(self.prefix_list_rules[0].get_absolute_url(), content)
        # The terminating deny-9999 rule belongs to the same list but is outside the constraint.
        denied = self.prefix_lists[0].rules.exclude(pk=self.prefix_list_rules[0].pk).first()
        self.assertIsNotNone(denied)
        self.assertNotIn(denied.get_absolute_url(), content)


class PrefixNotAChildTestCase(BaseTestData, TestCase):
    """`Prefix` objects with no static routes still render their detail page."""

    @classmethod
    def setUpTestData(cls):
        cls.build_topology()

    @override_settings(EXEMPT_VIEW_PERMISSIONS=['*'])
    def test_prefix_detail_renders_without_static_routes(self):
        prefix = Prefix.objects.get(pk=self.prefixes4[0].pk)
        self.assertHttpStatus(self.client.get(prefix.get_absolute_url()), 200)


class BGPPasswordFormTestCase(BaseTestData, TestCase):
    """
    The BGP MD5 key must never be written back into the edit page.

    ``PasswordInput(render_value=True)`` puts the stored key into the HTML as a
    ``value=`` attribute, so anyone with change permission — which is a far broader
    group than "people who should know the key" — can read it from the page source.
    Not rendering it makes a blank submission ambiguous, so the other half of the
    behaviour matters just as much: blank must preserve, and there has to be some way
    to deliberately remove a key.
    """

    SECRET = 'SUPERSECRET-MD5'

    @classmethod
    def setUpTestData(cls):
        cls.build_topology()

        cls.router = BGPRouter.objects.create(device=cls.devices[0], vrf=cls.vrfs[0])
        cls.peergroup = BGPPeergroup.objects.create(
            bgprouter=cls.router,
            name='PG-SECRET',
            remote_as=cls.asns[0],
            password=cls.SECRET,
        )
        cls.peer = BGPPeer.objects.create(
            bgprouter=cls.router,
            remote_address=cls.addresses4[0],
            remote_as=cls.asns[0],
            password=cls.SECRET,
        )

    def subjects(self):
        """(label, instance, base form data) for both password-bearing models."""
        return (
            (
                'bgppeergroup',
                self.peergroup,
                {
                    'bgprouter': self.router.pk,
                    'name': self.peergroup.name,
                    'remote_as': self.asns[0].pk,
                    'enable': 'on',
                    'bfd': 'on',
                },
            ),
            (
                'bgppeer',
                self.peer,
                {
                    'bgprouter': self.router.pk,
                    'remote_address': self.addresses4[0].pk,
                    'remote_as': self.asns[0].pk,
                    'enable': 'on',
                    'bfd': 'on',
                },
            ),
        )

    def edit_url(self, label, instance):
        return reverse(f'{URL_NAMESPACE}:{label}_edit', kwargs={'pk': instance.pk})

    def grant(self, label):
        """
        Change permission on the model, plus view permission on everything its
        DynamicModelChoiceFields select from — those querysets are restricted to what the
        user may see, so a related object the user cannot view is not a valid choice.

        That includes the model itself: the bulk edit form's ``pk`` field is restricted the
        same way, so without view permission the selected objects are not valid choices and
        the form fails with "Select a valid choice".
        """
        self.add_permissions(
            f'netbox_routing_protocols.change_{label}',
            f'netbox_routing_protocols.view_{label}',
            'netbox_routing_protocols.view_bgprouter',
            'netbox_routing_protocols.view_bgppeergroup',
            'ipam.view_asn',
            'ipam.view_ipaddress',
            'dcim.view_device',
            'dcim.view_interface',
        )

    def test_edit_form_html_never_contains_the_stored_key(self):
        for label, instance, _form_data in self.subjects():
            with self.subTest(model=label):
                self.grant(label)
                response = self.client.get(self.edit_url(label, instance))
                self.assertHttpStatus(response, 200)

                content = response.content.decode()
                self.assertNotIn(self.SECRET, content)
                # The field is still offered, so the absence above is not simply the
                # field having been dropped from the form.
                self.assertIn('name="password"', content)
                self.assertIn('name="clear_password"', content)

    def test_blank_password_preserves_the_stored_key(self):
        for label, instance, form_data in self.subjects():
            with self.subTest(model=label):
                self.grant(label)

                data = {**form_data, 'password': '', 'description': 'Edited without touching the key'}
                response = self.client.post(self.edit_url(label, instance), data)
                self.assertHttpStatus(response, 302)

                instance.refresh_from_db()
                self.assertEqual(instance.description, 'Edited without touching the key')
                self.assertEqual(instance.password, self.SECRET)

    def test_a_new_password_replaces_the_stored_key(self):
        for label, instance, form_data in self.subjects():
            with self.subTest(model=label):
                self.grant(label)

                data = {**form_data, 'password': 'ROTATED-MD5'}
                response = self.client.post(self.edit_url(label, instance), data)
                self.assertIn(response.status_code, (200, 302))

                instance.refresh_from_db()
                self.assertEqual(instance.password, 'ROTATED-MD5')

    def test_clear_password_removes_the_stored_key(self):
        """Blank must mean "unchanged", so there has to be an explicit way to remove a key."""
        for label, instance, form_data in self.subjects():
            with self.subTest(model=label):
                self.grant(label)

                data = {**form_data, 'password': '', 'clear_password': 'on'}
                response = self.client.post(self.edit_url(label, instance), data)
                self.assertIn(response.status_code, (200, 302))

                instance.refresh_from_db()
                self.assertEqual(instance.password, '')

    def test_setting_and_clearing_at_once_is_rejected(self):
        for label, instance, form_data in self.subjects():
            with self.subTest(model=label):
                self.grant(label)

                data = {**form_data, 'password': 'ROTATED-MD5', 'clear_password': 'on'}
                response = self.client.post(self.edit_url(label, instance), data)
                self.assertHttpStatus(response, 200)

                instance.refresh_from_db()
                self.assertEqual(instance.password, self.SECRET)

    def test_the_add_form_offers_no_clear_checkbox(self):
        """There is nothing to clear on an object that does not exist yet."""
        for label, _instance, _form_data in self.subjects():
            with self.subTest(model=label):
                self.add_permissions(
                    f'netbox_routing_protocols.add_{label}',
                    'netbox_routing_protocols.view_bgprouter',
                    'ipam.view_asn',
                )
                response = self.client.get(reverse(f'{URL_NAMESPACE}:{label}_add'))
                self.assertHttpStatus(response, 200)

                content = response.content.decode()
                self.assertIn('name="password"', content)
                self.assertNotIn('name="clear_password"', content)

    def test_bulk_edit_form_html_never_contains_a_stored_key(self):
        for label, instance, _form_data in self.subjects():
            with self.subTest(model=label):
                self.grant(label)
                response = self.client.post(
                    reverse(f'{URL_NAMESPACE}:{label}_bulk_edit'),
                    {'pk': [instance.pk], '_edit': ''},
                )
                self.assertHttpStatus(response, 200)
                self.assertNotIn(self.SECRET, response.content.decode())

    def test_bulk_edit_leaves_a_blank_password_alone(self):
        for label, instance, _form_data in self.subjects():
            with self.subTest(model=label):
                self.grant(label)
                response = self.client.post(
                    reverse(f'{URL_NAMESPACE}:{label}_bulk_edit'),
                    {'pk': [instance.pk], '_apply': '', 'password': '', 'description': 'Bulk edited'},
                )
                self.assertIn(response.status_code, (200, 302))

                instance.refresh_from_db()
                self.assertEqual(instance.description, 'Bulk edited')
                self.assertEqual(instance.password, self.SECRET)

    def test_bulk_edit_can_clear_a_password_through_set_null(self):
        for label, instance, _form_data in self.subjects():
            with self.subTest(model=label):
                self.grant(label)
                response = self.client.post(
                    reverse(f'{URL_NAMESPACE}:{label}_bulk_edit'),
                    {'pk': [instance.pk], '_apply': '', 'password': '', '_nullify': 'password'},
                )
                self.assertIn(response.status_code, (200, 302))

                instance.refresh_from_db()
                self.assertEqual(instance.password, '')
