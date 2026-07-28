"""
Model tests.

Coverage is weighted towards the things that are easy to get wrong and expensive
to get wrong in production:

* the ``name`` properties, which stand in for a real column and are used as the
  natural key in nested API representations;
* ``clean()`` cross-object validation;
* the database constraints, tested both through ``full_clean()`` (what the API
  and the forms hit) and through a direct write (proving the constraint really
  exists in PostgreSQL rather than only in Python);
* the ``post_save`` receiver that terminates new prefix lists and route maps;
* what happens to routing objects when the prefixes they reference are deleted.
"""

import uuid

from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.db.models.signals import post_save
from django.test import RequestFactory, TestCase, override_settings

from core.choices import ObjectChangeActionChoices
from core.models import ObjectChange
from ipam.models import Prefix
from netbox.context_managers import event_tracking
from users.models import User

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
from netbox_routing_protocols.signals import DEFAULT_DENY_SEQUENCE

from .base import PLUGINS_CONFIG_NO_DEFAULT_DENY, BaseTestData, create_ip_addresses, create_prefixes


def build_request(user):
    """
    A minimal request for ``event_tracking()``.

    NetBox writes ObjectChange rows from its post-save receivers, which no-op outside a
    request context. Model-level tests that need to assert on the change log therefore
    have to supply one.
    """
    request = RequestFactory().get('/')
    request.id = uuid.uuid4()
    request.user = user
    return request


class StaticRouteTestCase(BaseTestData, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.build_topology()

    def test_nexthop_is_required(self):
        """A route with no next hop cannot be rendered, so the column is NOT NULL."""
        self.assertFalse(StaticRoute._meta.get_field('nexthop').null)
        self.assertFalse(StaticRoute._meta.get_field('nexthop').blank)

    def test_name_returns_prefix(self):
        route = StaticRoute.objects.create(
            device=self.devices[0],
            vrf=self.vrfs[0],
            prefix=self.prefixes4[0],
            nexthop=self.addresses4[0],
        )
        self.assertEqual(route.name, '10.123.1.0/24')
        self.assertEqual(str(route), '10.123.1.0/24')

    def test_name_returns_ipv4_default_route(self):
        route = StaticRoute.objects.create(
            device=self.devices[0],
            vrf=self.vrfs[0],
            nexthop=self.addresses4[0],
            default_route=True,
        )
        self.assertEqual(route.name, '0.0.0.0/0')
        self.assertEqual(str(route), '0.0.0.0/0')

    def test_name_returns_ipv6_default_route(self):
        route = StaticRoute.objects.create(
            device=self.devices[0],
            vrf=self.vrfs[0],
            nexthop=self.addresses6[0],
            default_route=True,
        )
        self.assertEqual(route.name, '::/0')
        self.assertEqual(str(route), '::/0')

    def test_name_returns_ipv6_prefix(self):
        route = StaticRoute.objects.create(
            device=self.devices[0],
            vrf=self.vrfs[0],
            prefix=self.prefixes6[0],
            nexthop=self.addresses6[0],
        )
        self.assertEqual(route.name, '2001:db8:1::/48')

    def test_name_does_not_raise_on_unsaved_instance(self):
        """
        ``name`` is reached from form and serializer validation before a next hop
        has necessarily been bound, so it must degrade rather than raise.
        """
        self.assertEqual(StaticRoute().name, '0.0.0.0/0')
        self.assertEqual(StaticRoute(default_route=True).name, '0.0.0.0/0')
        self.assertEqual(StaticRoute(nexthop=self.addresses6[0], default_route=True).name, '::/0')
        self.assertEqual(StaticRoute(prefix=self.prefixes4[1], nexthop=self.addresses4[0]).name, '10.123.2.0/24')

    def test_clean_rejects_mismatched_address_family(self):
        route = StaticRoute(
            device=self.devices[0],
            vrf=self.vrfs[0],
            prefix=self.prefixes4[0],
            nexthop=self.addresses6[0],
        )
        with self.assertRaises(ValidationError) as ctx:
            route.full_clean()
        self.assertIn('nexthop', ctx.exception.message_dict)

    def test_clean_rejects_prefix_and_default_route(self):
        route = StaticRoute(
            device=self.devices[0],
            vrf=self.vrfs[0],
            prefix=self.prefixes4[0],
            nexthop=self.addresses4[0],
            default_route=True,
        )
        with self.assertRaises(ValidationError):
            route.full_clean()

    def test_clean_rejects_neither_prefix_nor_default_route(self):
        route = StaticRoute(
            device=self.devices[0],
            vrf=self.vrfs[0],
            nexthop=self.addresses4[0],
            default_route=False,
        )
        with self.assertRaises(ValidationError):
            route.full_clean()

    def test_database_rejects_prefix_and_default_route(self):
        """The mutual exclusion is a real CheckConstraint, not only a clean() rule."""
        with self.assertRaises(IntegrityError), transaction.atomic():
            StaticRoute.objects.create(
                device=self.devices[0],
                vrf=self.vrfs[0],
                prefix=self.prefixes4[0],
                nexthop=self.addresses4[0],
                default_route=True,
            )

    def test_database_rejects_neither_prefix_nor_default_route(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            StaticRoute.objects.create(
                device=self.devices[0],
                vrf=self.vrfs[0],
                nexthop=self.addresses4[0],
            )

    def test_duplicate_prefix_in_vrf_is_rejected(self):
        StaticRoute.objects.create(
            device=self.devices[0],
            vrf=self.vrfs[0],
            prefix=self.prefixes4[0],
            nexthop=self.addresses4[0],
        )
        duplicate = StaticRoute(
            device=self.devices[0],
            vrf=self.vrfs[0],
            prefix=self.prefixes4[0],
            nexthop=self.addresses4[1],
        )
        with self.assertRaises(ValidationError):
            duplicate.full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            duplicate.save()

    def test_duplicate_default_route_in_vrf_is_rejected(self):
        StaticRoute.objects.create(
            device=self.devices[0],
            vrf=self.vrfs[0],
            nexthop=self.addresses4[0],
            default_route=True,
        )
        duplicate = StaticRoute(
            device=self.devices[0],
            vrf=self.vrfs[0],
            nexthop=self.addresses4[0],
            default_route=True,
        )
        with self.assertRaises(ValidationError):
            duplicate.full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            duplicate.save()

    def test_duplicate_prefix_in_global_table_is_rejected(self):
        """
        Routes in the global table (vrf IS NULL) are covered by a partial unique
        constraint, not by a Python existence check. The direct save() below is the
        point of the test: a SELECT-then-INSERT in clean() would let two concurrent
        writers both commit, so the rejection has to come from the database.
        """
        StaticRoute.objects.create(
            device=self.devices[0],
            prefix=self.prefixes4[0],
            nexthop=self.addresses4[0],
        )
        duplicate = StaticRoute(
            device=self.devices[0],
            prefix=self.prefixes4[0],
            nexthop=self.addresses4[1],
        )
        with self.assertRaises(ValidationError) as ctx:
            duplicate.full_clean()
        self.assertIn(
            'A static route for this prefix already exists on this device in the global routing table.',
            ctx.exception.messages,
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            duplicate.save()

    def test_database_rejects_a_duplicate_global_prefix_written_without_validation(self):
        """A create() that never calls full_clean() — the API-race path — must still fail."""
        StaticRoute.objects.create(
            device=self.devices[0],
            prefix=self.prefixes4[0],
            nexthop=self.addresses4[0],
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            StaticRoute.objects.create(
                device=self.devices[0],
                prefix=self.prefixes4[0],
                nexthop=self.addresses4[1],
            )

    def test_duplicate_default_route_in_global_table_is_rejected(self):
        StaticRoute.objects.create(
            device=self.devices[0],
            nexthop=self.addresses4[0],
            default_route=True,
        )
        duplicate = StaticRoute(
            device=self.devices[0],
            nexthop=self.addresses4[0],
            default_route=True,
        )
        with self.assertRaises(ValidationError) as ctx:
            duplicate.full_clean()
        self.assertIn(
            'A default route to this next hop already exists on this device in the global routing table.',
            ctx.exception.messages,
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            duplicate.save()

    def test_database_rejects_a_duplicate_global_default_route_written_without_validation(self):
        StaticRoute.objects.create(
            device=self.devices[0],
            nexthop=self.addresses4[0],
            default_route=True,
        )
        with self.assertRaises(IntegrityError), transaction.atomic():
            StaticRoute.objects.create(
                device=self.devices[0],
                nexthop=self.addresses4[0],
                default_route=True,
            )

    def test_two_global_default_routes_to_different_next_hops_are_allowed(self):
        """
        The global-prefix constraint covers (device, prefix), and a default route has no
        prefix. NULLs compare as distinct, so ECMP defaults must not collide with it.
        """
        StaticRoute.objects.create(
            device=self.devices[0],
            nexthop=self.addresses4[0],
            default_route=True,
        )
        route = StaticRoute(
            device=self.devices[0],
            nexthop=self.addresses4[1],
            default_route=True,
        )
        route.full_clean()
        route.save()
        self.assertEqual(StaticRoute.objects.filter(device=self.devices[0], default_route=True).count(), 2)

    def test_the_same_global_prefix_is_allowed_alongside_a_vrf_copy(self):
        """The global constraints are conditional on vrf IS NULL and must not reach into a VRF."""
        StaticRoute.objects.create(
            device=self.devices[0],
            prefix=self.prefixes4[0],
            nexthop=self.addresses4[0],
        )
        route = StaticRoute(
            device=self.devices[0],
            vrf=self.vrfs[0],
            prefix=self.prefixes4[0],
            nexthop=self.addresses4[0],
        )
        route.full_clean()
        route.save()
        self.assertEqual(StaticRoute.objects.filter(prefix=self.prefixes4[0]).count(), 2)

    def test_same_prefix_on_another_device_is_allowed(self):
        StaticRoute.objects.create(
            device=self.devices[0],
            prefix=self.prefixes4[0],
            nexthop=self.addresses4[0],
        )
        route = StaticRoute(
            device=self.devices[1],
            prefix=self.prefixes4[0],
            nexthop=self.addresses4[0],
        )
        route.full_clean()
        route.save()
        self.assertEqual(StaticRoute.objects.filter(prefix=self.prefixes4[0]).count(), 2)


class PrefixListTestCase(BaseTestData, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.build_topology()

    def test_str(self):
        prefix_list = PrefixList.objects.create(
            name='PL-CORE-IN',
            device=self.devices[0],
            address_family=AddressFamilyChoices.FAMILY_IPV4,
        )
        self.assertEqual(str(prefix_list), 'PL-CORE-IN')

    def test_duplicate_name_on_device_is_rejected(self):
        PrefixList.objects.create(
            name='PL-1',
            device=self.devices[0],
            address_family=AddressFamilyChoices.FAMILY_IPV4,
        )
        duplicate = PrefixList(
            name='PL-1',
            device=self.devices[0],
            address_family=AddressFamilyChoices.FAMILY_IPV6,
        )
        with self.assertRaises(ValidationError):
            duplicate.full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            duplicate.save()

    def test_same_name_on_another_device_is_allowed(self):
        PrefixList.objects.create(
            name='PL-1',
            device=self.devices[0],
            address_family=AddressFamilyChoices.FAMILY_IPV4,
        )
        prefix_list = PrefixList(
            name='PL-1',
            device=self.devices[1],
            address_family=AddressFamilyChoices.FAMILY_IPV4,
        )
        prefix_list.full_clean()
        prefix_list.save()
        self.assertEqual(PrefixList.objects.filter(name='PL-1').count(), 2)


@override_settings(PLUGINS_CONFIG=PLUGINS_CONFIG_NO_DEFAULT_DENY)
class PrefixListRuleTestCase(BaseTestData, TestCase):
    """The terminating rule is switched off here so rule counts are unambiguous."""

    @classmethod
    def setUpTestData(cls):
        cls.build_topology()
        with override_settings(PLUGINS_CONFIG=PLUGINS_CONFIG_NO_DEFAULT_DENY):
            cls.prefix_list4 = PrefixList.objects.create(
                name='PL-V4',
                device=cls.devices[0],
                address_family=AddressFamilyChoices.FAMILY_IPV4,
            )
            cls.prefix_list6 = PrefixList.objects.create(
                name='PL-V6',
                device=cls.devices[0],
                address_family=AddressFamilyChoices.FAMILY_IPV6,
            )

    def test_name(self):
        rule = PrefixListRule.objects.create(
            prefix_list=self.prefix_list4,
            sequence=10,
            action=ActionChoices.ACTION_PERMIT,
            prefix=self.prefixes4[0],
        )
        self.assertEqual(rule.name, 'PL-V4 10')
        self.assertEqual(str(rule), 'PL-V4 10')

    def test_exactly_one_match_type_is_required(self):
        base = {
            'prefix_list': self.prefix_list4,
            'sequence': 10,
            'action': ActionChoices.ACTION_PERMIT,
        }
        invalid = (
            # None of the three
            {},
            # Two at once
            {'prefix': self.prefixes4[0], 'match_any': True},
            {'prefix': self.prefixes4[0], 'match_default': True},
            {'match_any': True, 'match_default': True},
            # All three
            {'prefix': self.prefixes4[0], 'match_any': True, 'match_default': True},
        )
        for extra in invalid:
            with self.subTest(extra=extra):
                with self.assertRaises(ValidationError):
                    PrefixListRule(**base, **extra).full_clean()

    def test_database_rejects_multiple_match_types(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            PrefixListRule.objects.create(
                prefix_list=self.prefix_list4,
                sequence=10,
                action=ActionChoices.ACTION_PERMIT,
                prefix=self.prefixes4[0],
                match_any=True,
            )

    def test_each_match_type_alone_is_valid(self):
        valid = (
            {'prefix': self.prefixes4[0]},
            {'match_any': True},
            {'match_default': True},
        )
        for sequence, extra in enumerate(valid, start=1):
            with self.subTest(extra=extra):
                rule = PrefixListRule(
                    prefix_list=self.prefix_list4,
                    sequence=sequence,
                    action=ActionChoices.ACTION_PERMIT,
                    **extra,
                )
                rule.full_clean()
                rule.save()
        self.assertEqual(self.prefix_list4.rules.count(), 3)

    def test_duplicate_sequence_is_rejected(self):
        PrefixListRule.objects.create(
            prefix_list=self.prefix_list4,
            sequence=10,
            action=ActionChoices.ACTION_PERMIT,
            prefix=self.prefixes4[0],
        )
        duplicate = PrefixListRule(
            prefix_list=self.prefix_list4,
            sequence=10,
            action=ActionChoices.ACTION_DENY,
            prefix=self.prefixes4[1],
        )
        with self.assertRaises(ValidationError):
            duplicate.full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            duplicate.save()

    def test_clean_rejects_prefix_from_another_address_family(self):
        rule = PrefixListRule(
            prefix_list=self.prefix_list4,
            sequence=10,
            action=ActionChoices.ACTION_PERMIT,
            prefix=self.prefixes6[0],
        )
        with self.assertRaises(ValidationError) as ctx:
            rule.full_clean()
        self.assertIn('prefix', ctx.exception.message_dict)

    def test_clean_rejects_inverted_prefix_lengths(self):
        rule = PrefixListRule(
            prefix_list=self.prefix_list4,
            sequence=10,
            action=ActionChoices.ACTION_PERMIT,
            prefix=self.prefixes4[0],
            min_prefix_length=25,
            max_prefix_length=24,
        )
        with self.assertRaises(ValidationError) as ctx:
            rule.full_clean()
        self.assertIn('max_prefix_length', ctx.exception.message_dict)

    def test_clean_allows_equal_prefix_lengths(self):
        """``ge 24 le 24`` is how every mainstream platform spells "exactly a /24"."""
        rule = PrefixListRule(
            prefix_list=self.prefix_list4,
            sequence=11,
            action=ActionChoices.ACTION_PERMIT,
            prefix=self.prefixes4[0],
            min_prefix_length=24,
            max_prefix_length=24,
        )
        rule.full_clean()
        rule.save()

        rule.refresh_from_db()
        self.assertEqual(rule.min_prefix_length, 24)
        self.assertEqual(rule.max_prefix_length, 24)

    def test_clean_bounds_prefix_length_to_address_family(self):
        """A /64 is legal in an IPv6 list but not in an IPv4 one."""
        ipv4_rule = PrefixListRule(
            prefix_list=self.prefix_list4,
            sequence=10,
            action=ActionChoices.ACTION_PERMIT,
            prefix=self.prefixes4[0],
            max_prefix_length=64,
        )
        with self.assertRaises(ValidationError) as ctx:
            ipv4_rule.full_clean()
        self.assertIn('max_prefix_length', ctx.exception.message_dict)

        ipv6_rule = PrefixListRule(
            prefix_list=self.prefix_list6,
            sequence=10,
            action=ActionChoices.ACTION_PERMIT,
            prefix=self.prefixes6[0],
            max_prefix_length=64,
        )
        ipv6_rule.full_clean()


class RouteMapTestCase(BaseTestData, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.build_topology()

    def test_str(self):
        route_map = RouteMap.objects.create(name='RM-CORE-OUT', device=self.devices[0])
        self.assertEqual(str(route_map), 'RM-CORE-OUT')

    def test_duplicate_name_on_device_is_rejected(self):
        RouteMap.objects.create(name='RM-1', device=self.devices[0])
        duplicate = RouteMap(name='RM-1', device=self.devices[0])
        with self.assertRaises(ValidationError):
            duplicate.full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            duplicate.save()


@override_settings(PLUGINS_CONFIG=PLUGINS_CONFIG_NO_DEFAULT_DENY)
class RouteMapRuleTestCase(BaseTestData, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.build_topology()
        with override_settings(PLUGINS_CONFIG=PLUGINS_CONFIG_NO_DEFAULT_DENY):
            cls.route_map = RouteMap.objects.create(name='RM-1', device=cls.devices[0])
            cls.prefix_list = PrefixList.objects.create(
                name='PL-1',
                device=cls.devices[0],
                address_family=AddressFamilyChoices.FAMILY_IPV4,
            )
            cls.other_prefix_list = PrefixList.objects.create(
                name='PL-1',
                device=cls.devices[1],
                address_family=AddressFamilyChoices.FAMILY_IPV4,
            )

    def test_name(self):
        rule = RouteMapRule.objects.create(
            route_map=self.route_map,
            sequence=10,
            action=ActionChoices.ACTION_PERMIT,
            prefix_list=self.prefix_list,
        )
        self.assertEqual(rule.name, 'RM-1 10')
        self.assertEqual(str(rule), 'RM-1 10')

    def test_exactly_one_match_type_is_required(self):
        base = {
            'route_map': self.route_map,
            'sequence': 10,
            'action': ActionChoices.ACTION_PERMIT,
        }
        invalid = (
            {},
            {'prefix_list': self.prefix_list, 'match_any': True},
        )
        for extra in invalid:
            with self.subTest(extra=extra):
                with self.assertRaises(ValidationError):
                    RouteMapRule(**base, **extra).full_clean()

    def test_database_rejects_multiple_match_types(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            RouteMapRule.objects.create(
                route_map=self.route_map,
                sequence=10,
                action=ActionChoices.ACTION_PERMIT,
                prefix_list=self.prefix_list,
                match_any=True,
            )

    def test_duplicate_sequence_is_rejected(self):
        RouteMapRule.objects.create(
            route_map=self.route_map,
            sequence=10,
            action=ActionChoices.ACTION_PERMIT,
            match_any=True,
        )
        duplicate = RouteMapRule(
            route_map=self.route_map,
            sequence=10,
            action=ActionChoices.ACTION_DENY,
            prefix_list=self.prefix_list,
        )
        with self.assertRaises(ValidationError):
            duplicate.full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            duplicate.save()

    def test_clean_rejects_prefix_list_from_another_device(self):
        rule = RouteMapRule(
            route_map=self.route_map,
            sequence=10,
            action=ActionChoices.ACTION_PERMIT,
            prefix_list=self.other_prefix_list,
        )
        with self.assertRaises(ValidationError) as ctx:
            rule.full_clean()
        self.assertIn('prefix_list', ctx.exception.message_dict)

    def test_prefix_list_referenced_by_a_rule_is_protected(self):
        RouteMapRule.objects.create(
            route_map=self.route_map,
            sequence=10,
            action=ActionChoices.ACTION_PERMIT,
            prefix_list=self.prefix_list,
        )
        with self.assertRaises(models.ProtectedError), transaction.atomic():
            self.prefix_list.delete()


class BGPRouterTestCase(BaseTestData, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.build_topology()

    def test_route_reflection_field_is_spelled_correctly(self):
        field = BGPRouter._meta.get_field('route_reflection')
        self.assertEqual(field.verbose_name, 'Route Reflection')

    def test_name_and_str(self):
        router = BGPRouter.objects.create(device=self.devices[0], vrf=self.vrfs[0])
        self.assertEqual(router.name, 'core-sw1 :: VRF 1')
        self.assertEqual(str(router), 'core-sw1 :: VRF 1')

    def test_duplicate_device_and_vrf_is_rejected(self):
        BGPRouter.objects.create(device=self.devices[0], vrf=self.vrfs[0])
        duplicate = BGPRouter(device=self.devices[0], vrf=self.vrfs[0])
        with self.assertRaises(ValidationError):
            duplicate.full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            duplicate.save()

    def test_clean_accepts_router_id_on_the_device_and_vrf(self):
        router_id = create_ip_addresses('10.123.9.1/32', vrf=self.vrfs[0], assigned_object=self.interfaces1[0])[0]
        router = BGPRouter(device=self.devices[0], vrf=self.vrfs[0], router_id=router_id)
        router.full_clean()

    def test_clean_rejects_router_id_on_another_device(self):
        router_id = create_ip_addresses('10.123.9.2/32', vrf=self.vrfs[0], assigned_object=self.interfaces2[0])[0]
        router = BGPRouter(device=self.devices[0], vrf=self.vrfs[0], router_id=router_id)
        with self.assertRaises(ValidationError) as ctx:
            router.full_clean()
        self.assertIn('router_id', ctx.exception.message_dict)

    def test_clean_rejects_unassigned_router_id(self):
        router_id = create_ip_addresses('10.123.9.3/32', vrf=self.vrfs[0])[0]
        router = BGPRouter(device=self.devices[0], vrf=self.vrfs[0], router_id=router_id)
        with self.assertRaises(ValidationError) as ctx:
            router.full_clean()
        self.assertIn('router_id', ctx.exception.message_dict)

    def test_clean_rejects_router_id_in_another_vrf(self):
        router_id = create_ip_addresses('10.123.9.4/32', vrf=self.vrfs[1], assigned_object=self.interfaces1[1])[0]
        router = BGPRouter(device=self.devices[0], vrf=self.vrfs[0], router_id=router_id)
        with self.assertRaises(ValidationError) as ctx:
            router.full_clean()
        self.assertIn('router_id', ctx.exception.message_dict)


class BGPPeergroupTestCase(BaseTestData, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.build_topology()
        cls.router = BGPRouter.objects.create(device=cls.devices[0], vrf=cls.vrfs[0])
        cls.other_router = BGPRouter.objects.create(device=cls.devices[1], vrf=cls.vrfs[0])

    def test_has_no_device_or_vrf_columns(self):
        """Device and VRF are fixed by the BGP router; duplicating them invites drift."""
        columns = {field.name for field in BGPPeergroup._meta.fields}
        self.assertNotIn('device', columns)
        self.assertNotIn('vrf', columns)

    def test_device_and_vrf_proxy_through_the_router(self):
        peergroup = BGPPeergroup.objects.create(
            bgprouter=self.router,
            name='PG-1',
            remote_as=self.asns[0],
        )
        self.assertEqual(peergroup.device, self.devices[0])
        self.assertEqual(peergroup.vrf, self.vrfs[0])
        self.assertEqual(str(peergroup), 'PG-1')

    def test_duplicate_name_on_router_is_rejected(self):
        BGPPeergroup.objects.create(bgprouter=self.router, name='PG-1', remote_as=self.asns[0])
        duplicate = BGPPeergroup(bgprouter=self.router, name='PG-1', remote_as=self.asns[1])
        with self.assertRaises(ValidationError):
            duplicate.full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            duplicate.save()

    def test_same_name_on_another_router_is_allowed(self):
        BGPPeergroup.objects.create(bgprouter=self.router, name='PG-1', remote_as=self.asns[0])
        peergroup = BGPPeergroup(bgprouter=self.other_router, name='PG-1', remote_as=self.asns[0])
        peergroup.full_clean()
        peergroup.save()
        self.assertEqual(BGPPeergroup.objects.filter(name='PG-1').count(), 2)

    def test_clean_rejects_multihop_ttl_without_multihop(self):
        peergroup = BGPPeergroup(
            bgprouter=self.router,
            name='PG-2',
            remote_as=self.asns[0],
            ebgp_multihop=False,
            ebgp_multihop_ttl=5,
        )
        with self.assertRaises(ValidationError) as ctx:
            peergroup.full_clean()
        self.assertIn('ebgp_multihop_ttl', ctx.exception.message_dict)


class BGPPeerTestCase(BaseTestData, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.build_topology()
        cls.router = BGPRouter.objects.create(device=cls.devices[0], vrf=cls.vrfs[0])
        cls.other_router = BGPRouter.objects.create(device=cls.devices[1], vrf=cls.vrfs[0])
        cls.peergroup = BGPPeergroup.objects.create(bgprouter=cls.router, name='PG-1', remote_as=cls.asns[0])
        cls.other_peergroup = BGPPeergroup.objects.create(
            bgprouter=cls.other_router, name='PG-2', remote_as=cls.asns[0]
        )

    def test_has_no_device_or_vrf_columns(self):
        columns = {field.name for field in BGPPeer._meta.fields}
        self.assertNotIn('device', columns)
        self.assertNotIn('vrf', columns)

    def test_name_from_remote_address(self):
        peer = BGPPeer.objects.create(
            bgprouter=self.router,
            remote_address=self.addresses4[0],
            remote_as=self.asns[0],
        )
        self.assertEqual(peer.name, '10.123.1.1/24')
        self.assertEqual(str(peer), '10.123.1.1/24')
        self.assertEqual(peer.device, self.devices[0])
        self.assertEqual(peer.vrf, self.vrfs[0])

    def test_name_from_interface(self):
        peer = BGPPeer.objects.create(
            bgprouter=self.router,
            interface=self.interfaces1[0],
            remote_as=self.asns[0],
        )
        self.assertEqual(peer.name, 'Ethernet1')
        self.assertEqual(str(peer), 'Ethernet1')

    def test_name_does_not_raise_on_unsaved_instance(self):
        """
        A saved row always has an address or an interface under the CheckConstraint, but
        the property is reached from unsaved instances during form and serializer
        validation — where raising AttributeError would surface as a 500, not a 400.
        """
        peer = BGPPeer(bgprouter=self.router, remote_as=self.asns[0])
        self.assertEqual(peer.name, '')
        self.assertEqual(str(peer), '')

    def test_address_and_interface_are_mutually_exclusive(self):
        both = BGPPeer(
            bgprouter=self.router,
            remote_address=self.addresses4[0],
            interface=self.interfaces1[0],
            remote_as=self.asns[0],
        )
        with self.assertRaises(ValidationError):
            both.full_clean()

        neither = BGPPeer(bgprouter=self.router, remote_as=self.asns[0])
        with self.assertRaises(ValidationError):
            neither.full_clean()

    def test_database_rejects_address_and_interface_together(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            BGPPeer.objects.create(
                bgprouter=self.router,
                remote_address=self.addresses4[0],
                interface=self.interfaces1[0],
                remote_as=self.asns[0],
            )

    def test_database_rejects_neither_address_nor_interface(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            BGPPeer.objects.create(bgprouter=self.router, remote_as=self.asns[0])

    def test_duplicate_remote_address_on_router_is_rejected(self):
        BGPPeer.objects.create(bgprouter=self.router, remote_address=self.addresses4[0], remote_as=self.asns[0])
        duplicate = BGPPeer(bgprouter=self.router, remote_address=self.addresses4[0], remote_as=self.asns[1])
        with self.assertRaises(ValidationError):
            duplicate.full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            duplicate.save()

    def test_duplicate_interface_on_router_is_rejected(self):
        BGPPeer.objects.create(bgprouter=self.router, interface=self.interfaces1[0], remote_as=self.asns[0])
        duplicate = BGPPeer(bgprouter=self.router, interface=self.interfaces1[0], remote_as=self.asns[1])
        with self.assertRaises(ValidationError):
            duplicate.full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            duplicate.save()

    def test_clean_rejects_peergroup_on_another_router(self):
        peer = BGPPeer(
            bgprouter=self.router,
            remote_address=self.addresses4[0],
            remote_as=self.asns[0],
            peergroup=self.other_peergroup,
        )
        with self.assertRaises(ValidationError) as ctx:
            peer.full_clean()
        self.assertIn('peergroup', ctx.exception.message_dict)

    def test_clean_rejects_interface_on_another_device(self):
        peer = BGPPeer(
            bgprouter=self.router,
            interface=self.interfaces2[0],
            remote_as=self.asns[0],
        )
        with self.assertRaises(ValidationError) as ctx:
            peer.full_clean()
        self.assertIn('interface', ctx.exception.message_dict)

    def test_clean_rejects_interface_in_another_vrf(self):
        router = BGPRouter.objects.create(device=self.devices[0], vrf=self.vrfs[1])
        peer = BGPPeer(
            bgprouter=router,
            interface=self.interfaces1[0],
            remote_as=self.asns[0],
        )
        with self.assertRaises(ValidationError) as ctx:
            peer.full_clean()
        self.assertIn('interface', ctx.exception.message_dict)

    def test_peergroup_in_use_is_protected(self):
        BGPPeer.objects.create(
            bgprouter=self.router,
            remote_address=self.addresses4[0],
            remote_as=self.asns[0],
            peergroup=self.peergroup,
        )
        with self.assertRaises(models.ProtectedError), transaction.atomic():
            self.peergroup.delete()


class BGPAddressFamilyTestCase(BaseTestData, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.build_topology()
        cls.router = BGPRouter.objects.create(device=cls.devices[0], vrf=cls.vrfs[0])
        cls.route_map = RouteMap.objects.create(name='RM-1', device=cls.devices[0])
        cls.other_route_map = RouteMap.objects.create(name='RM-2', device=cls.devices[1])

    def test_has_no_device_or_vrf_columns(self):
        columns = {field.name for field in BGPAddressFamily._meta.fields}
        self.assertNotIn('device', columns)
        self.assertNotIn('vrf', columns)

    def test_str_and_proxied_attributes(self):
        family = BGPAddressFamily.objects.create(
            bgprouter=self.router,
            family=BGPAddressFamilyChoices.AFI_IPV4_UNICAST,
        )
        self.assertEqual(str(family), 'IPv4 Unicast')
        self.assertEqual(family.device, self.devices[0])
        self.assertEqual(family.vrf, self.vrfs[0])

    def test_duplicate_family_on_router_is_rejected(self):
        BGPAddressFamily.objects.create(bgprouter=self.router, family=BGPAddressFamilyChoices.AFI_IPV4_UNICAST)
        duplicate = BGPAddressFamily(bgprouter=self.router, family=BGPAddressFamilyChoices.AFI_IPV4_UNICAST)
        with self.assertRaises(ValidationError):
            duplicate.full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            duplicate.save()

    def test_clean_rejects_route_maps_from_another_device(self):
        for field in ('aggregate_route_map', 'network_route_map'):
            with self.subTest(field=field):
                family = BGPAddressFamily(
                    bgprouter=self.router,
                    family=BGPAddressFamilyChoices.AFI_IPV4_UNICAST,
                    **{field: self.other_route_map},
                )
                with self.assertRaises(ValidationError) as ctx:
                    family.full_clean()
                self.assertIn(field, ctx.exception.message_dict)

    def test_clean_accepts_route_maps_from_the_same_device(self):
        family = BGPAddressFamily(
            bgprouter=self.router,
            family=BGPAddressFamilyChoices.AFI_IPV4_UNICAST,
            aggregate_route_map=self.route_map,
            network_route_map=self.route_map,
        )
        family.full_clean()

    def test_route_map_in_use_is_protected(self):
        BGPAddressFamily.objects.create(
            bgprouter=self.router,
            family=BGPAddressFamilyChoices.AFI_IPV4_UNICAST,
            aggregate_route_map=self.route_map,
        )
        with self.assertRaises(models.ProtectedError), transaction.atomic():
            self.route_map.delete()


class BGPAddressFamilyRedistributeTestCase(BaseTestData, TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.build_topology()
        cls.router = BGPRouter.objects.create(device=cls.devices[0], vrf=cls.vrfs[0])
        cls.family = BGPAddressFamily.objects.create(
            bgprouter=cls.router, family=BGPAddressFamilyChoices.AFI_IPV4_UNICAST
        )
        cls.route_map = RouteMap.objects.create(name='RM-1', device=cls.devices[0])
        cls.other_route_map = RouteMap.objects.create(name='RM-2', device=cls.devices[1])

    def test_name_and_str(self):
        redistribution = BGPAddressFamilyRedistribute.objects.create(
            family=self.family,
            protocol=BGPRedistributeProtocolChoices.PROTOCOL_CONNECTED,
        )
        self.assertEqual(str(redistribution), 'IPv4 Unicast :: Connected')
        self.assertEqual(redistribution.name, 'IPv4 Unicast :: Connected')

    def test_duplicate_protocol_in_family_is_rejected(self):
        BGPAddressFamilyRedistribute.objects.create(
            family=self.family, protocol=BGPRedistributeProtocolChoices.PROTOCOL_STATIC
        )
        duplicate = BGPAddressFamilyRedistribute(
            family=self.family, protocol=BGPRedistributeProtocolChoices.PROTOCOL_STATIC
        )
        with self.assertRaises(ValidationError):
            duplicate.full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            duplicate.save()

    def test_clean_rejects_route_map_from_another_device(self):
        redistribution = BGPAddressFamilyRedistribute(
            family=self.family,
            protocol=BGPRedistributeProtocolChoices.PROTOCOL_STATIC,
            route_map=self.other_route_map,
        )
        with self.assertRaises(ValidationError) as ctx:
            redistribution.full_clean()
        self.assertIn('route_map', ctx.exception.message_dict)

    def test_clean_accepts_route_map_from_the_same_device(self):
        redistribution = BGPAddressFamilyRedistribute(
            family=self.family,
            protocol=BGPRedistributeProtocolChoices.PROTOCOL_STATIC,
            route_map=self.route_map,
        )
        redistribution.full_clean()


class BGPSessionAddressFamilyTestCase(BaseTestData, TestCase):
    """Covers both concrete subclasses of BGPSessionAddressFamilyAttributes."""

    @classmethod
    def setUpTestData(cls):
        cls.build_topology()
        cls.router = BGPRouter.objects.create(device=cls.devices[0], vrf=cls.vrfs[0])
        cls.peer = BGPPeer.objects.create(bgprouter=cls.router, remote_address=cls.addresses4[0], remote_as=cls.asns[0])
        cls.peergroup = BGPPeergroup.objects.create(bgprouter=cls.router, name='PG-1', remote_as=cls.asns[0])
        cls.route_map = RouteMap.objects.create(name='RM-1', device=cls.devices[0])
        cls.other_route_map = RouteMap.objects.create(name='RM-2', device=cls.devices[1])

    def test_owners_are_real_foreign_keys(self):
        """
        Peer and peer group address families each get a concrete FK rather than
        sharing one model through a generic relation.
        """
        peer_field = BGPPeerAddressFamily._meta.get_field('peer')
        self.assertIsInstance(peer_field, models.ForeignKey)
        self.assertIs(peer_field.related_model, BGPPeer)

        peergroup_field = BGPPeergroupAddressFamily._meta.get_field('peergroup')
        self.assertIsInstance(peergroup_field, models.ForeignKey)
        self.assertIs(peergroup_field.related_model, BGPPeergroup)

    def test_peer_address_family_name_and_str(self):
        family = BGPPeerAddressFamily.objects.create(peer=self.peer, family=BGPAddressFamilyChoices.AFI_IPV4_UNICAST)
        self.assertEqual(str(family), '10.123.1.1/24 :: IPv4 Unicast')
        self.assertEqual(family.name, '10.123.1.1/24 :: IPv4 Unicast')

    def test_peergroup_address_family_name_and_str(self):
        family = BGPPeergroupAddressFamily.objects.create(
            peergroup=self.peergroup, family=BGPAddressFamilyChoices.AFI_IPV6_UNICAST
        )
        self.assertEqual(str(family), 'PG-1 :: IPv6 Unicast')
        self.assertEqual(family.name, 'PG-1 :: IPv6 Unicast')

    def test_duplicate_family_on_peer_is_rejected(self):
        BGPPeerAddressFamily.objects.create(peer=self.peer, family=BGPAddressFamilyChoices.AFI_IPV4_UNICAST)
        duplicate = BGPPeerAddressFamily(peer=self.peer, family=BGPAddressFamilyChoices.AFI_IPV4_UNICAST)
        with self.assertRaises(ValidationError):
            duplicate.full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            duplicate.save()

    def test_duplicate_family_on_peergroup_is_rejected(self):
        BGPPeergroupAddressFamily.objects.create(
            peergroup=self.peergroup, family=BGPAddressFamilyChoices.AFI_IPV4_UNICAST
        )
        duplicate = BGPPeergroupAddressFamily(peergroup=self.peergroup, family=BGPAddressFamilyChoices.AFI_IPV4_UNICAST)
        with self.assertRaises(ValidationError):
            duplicate.full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            duplicate.save()

    def test_peer_clean_rejects_policies_from_another_device(self):
        for field in ('inbound_policy', 'outbound_policy'):
            with self.subTest(field=field):
                family = BGPPeerAddressFamily(
                    peer=self.peer,
                    family=BGPAddressFamilyChoices.AFI_IPV4_UNICAST,
                    **{field: self.other_route_map},
                )
                with self.assertRaises(ValidationError) as ctx:
                    family.full_clean()
                self.assertIn(field, ctx.exception.message_dict)

    def test_peergroup_clean_rejects_policies_from_another_device(self):
        for field in ('inbound_policy', 'outbound_policy'):
            with self.subTest(field=field):
                family = BGPPeergroupAddressFamily(
                    peergroup=self.peergroup,
                    family=BGPAddressFamilyChoices.AFI_IPV4_UNICAST,
                    **{field: self.other_route_map},
                )
                with self.assertRaises(ValidationError) as ctx:
                    family.full_clean()
                self.assertIn(field, ctx.exception.message_dict)

    def test_clean_accepts_policies_from_the_same_device(self):
        peer_family = BGPPeerAddressFamily(
            peer=self.peer,
            family=BGPAddressFamilyChoices.AFI_IPV4_UNICAST,
            inbound_policy=self.route_map,
            outbound_policy=self.route_map,
        )
        peer_family.full_clean()

        peergroup_family = BGPPeergroupAddressFamily(
            peergroup=self.peergroup,
            family=BGPAddressFamilyChoices.AFI_IPV4_UNICAST,
            inbound_policy=self.route_map,
            outbound_policy=self.route_map,
        )
        peergroup_family.full_clean()

    def test_deleting_a_peer_removes_its_address_families(self):
        BGPPeerAddressFamily.objects.create(peer=self.peer, family=BGPAddressFamilyChoices.AFI_IPV4_UNICAST)
        self.peer.delete()
        self.assertFalse(BGPPeerAddressFamily.objects.exists())


class DefaultDenyRuleSignalTestCase(BaseTestData, TestCase):
    """The post_save receivers that terminate new prefix lists and route maps."""

    @classmethod
    def setUpTestData(cls):
        cls.build_topology()

    def test_new_prefix_list_gets_exactly_one_deny_rule(self):
        prefix_list = PrefixList.objects.create(
            name='PL-1',
            device=self.devices[0],
            address_family=AddressFamilyChoices.FAMILY_IPV4,
        )
        rules = prefix_list.rules.all()
        self.assertEqual(len(rules), 1)
        rule = rules[0]
        self.assertEqual(rule.sequence, DEFAULT_DENY_SEQUENCE)
        self.assertEqual(rule.action, ActionChoices.ACTION_DENY)
        self.assertTrue(rule.match_any)
        self.assertFalse(rule.match_default)
        self.assertIsNone(rule.prefix)

    def test_new_route_map_gets_exactly_one_deny_rule(self):
        route_map = RouteMap.objects.create(name='RM-1', device=self.devices[0])
        rules = route_map.rules.all()
        self.assertEqual(len(rules), 1)
        rule = rules[0]
        self.assertEqual(rule.sequence, DEFAULT_DENY_SEQUENCE)
        self.assertEqual(rule.action, ActionChoices.ACTION_DENY)
        self.assertTrue(rule.match_any)
        self.assertIsNone(rule.prefix_list)

    def test_updating_does_not_add_another_rule(self):
        prefix_list = PrefixList.objects.create(
            name='PL-1',
            device=self.devices[0],
            address_family=AddressFamilyChoices.FAMILY_IPV4,
        )
        route_map = RouteMap.objects.create(name='RM-1', device=self.devices[0])

        prefix_list.description = 'Updated'
        prefix_list.save()
        route_map.description = 'Updated'
        route_map.save()

        self.assertEqual(prefix_list.rules.count(), 1)
        self.assertEqual(route_map.rules.count(), 1)

    @override_settings(PLUGINS_CONFIG=PLUGINS_CONFIG_NO_DEFAULT_DENY)
    def test_no_rule_when_the_setting_is_disabled(self):
        prefix_list = PrefixList.objects.create(
            name='PL-2',
            device=self.devices[0],
            address_family=AddressFamilyChoices.FAMILY_IPV4,
        )
        route_map = RouteMap.objects.create(name='RM-2', device=self.devices[0])

        self.assertEqual(prefix_list.rules.count(), 0)
        self.assertEqual(route_map.rules.count(), 0)

    @override_settings(PLUGINS_CONFIG=PLUGINS_CONFIG_NO_DEFAULT_DENY)
    def test_receivers_do_not_fire_for_raw_fixture_loading(self):
        """
        loaddata sends post_save with raw=True and unresolved relations; creating
        related rows at that point would corrupt the load. The receivers must
        bail out, which they do independently of the plugin setting.
        """
        prefix_list = PrefixList.objects.create(
            name='PL-3',
            device=self.devices[0],
            address_family=AddressFamilyChoices.FAMILY_IPV4,
        )
        route_map = RouteMap.objects.create(name='RM-3', device=self.devices[0])

        with override_settings():
            post_save.send(sender=PrefixList, instance=prefix_list, created=True, raw=True)
            post_save.send(sender=RouteMap, instance=route_map, created=True, raw=True)

        self.assertEqual(prefix_list.rules.count(), 0)
        self.assertEqual(route_map.rules.count(), 0)

    def test_receivers_do_not_fire_for_raw_loading_with_the_setting_enabled(self):
        prefix_list = PrefixList.objects.create(
            name='PL-4',
            device=self.devices[0],
            address_family=AddressFamilyChoices.FAMILY_IPV4,
        )
        route_map = RouteMap.objects.create(name='RM-4', device=self.devices[0])
        # One rule each, from the ordinary create above.
        self.assertEqual(prefix_list.rules.count(), 1)
        self.assertEqual(route_map.rules.count(), 1)

        post_save.send(sender=PrefixList, instance=prefix_list, created=True, raw=True)
        post_save.send(sender=RouteMap, instance=route_map, created=True, raw=True)

        self.assertEqual(prefix_list.rules.count(), 1)
        self.assertEqual(route_map.rules.count(), 1)


class BGPPrefixRemovalSignalTestCase(BaseTestData, TestCase):
    """Deleting a prefix should strip it from BGP aggregate and network statements."""

    @classmethod
    def setUpTestData(cls):
        cls.build_topology()
        cls.router = BGPRouter.objects.create(device=cls.devices[0], vrf=cls.vrfs[0])
        cls.user = User.objects.create_user(username='prefix-removal')

    def test_deleting_a_prefix_removes_it_from_the_address_family(self):
        family = BGPAddressFamily.objects.create(bgprouter=self.router, family=BGPAddressFamilyChoices.AFI_IPV4_UNICAST)
        family.aggregate_routes.set([self.prefixes4[0], self.prefixes4[1]])
        family.networks.set([self.prefixes4[0]])

        self.prefixes4[0].delete()

        family.refresh_from_db()
        self.assertEqual(list(family.aggregate_routes.all()), [self.prefixes4[1]])
        self.assertEqual(list(family.networks.all()), [])

    def test_deleting_a_prefix_records_the_removal_in_the_change_log(self):
        """
        The M2M rows would be dropped silently by the cascade; producing a change log
        entry is the entire reason this receiver exists, so asserting only that the rows
        went away would leave the actual behaviour untested. Change logging is driven by
        request context, hence event_tracking().
        """
        family = BGPAddressFamily.objects.create(bgprouter=self.router, family=BGPAddressFamilyChoices.AFI_IPV4_UNICAST)
        family.aggregate_routes.set([self.prefixes4[0], self.prefixes4[1]])
        family.networks.set([self.prefixes4[0]])

        removed_pk = self.prefixes4[0].pk
        kept_pk = self.prefixes4[1].pk

        request = build_request(self.user)
        with event_tracking(request):
            self.prefixes4[0].delete()

        change = ObjectChange.objects.get(
            changed_object_type=ContentType.objects.get_for_model(BGPAddressFamily),
            changed_object_id=family.pk,
        )
        self.assertEqual(change.action, ObjectChangeActionChoices.ACTION_UPDATE)
        self.assertEqual(change.request_id, request.id)

        # The prefix is gone from the "after" picture but still present in the "before" one,
        # which is what makes the change log a usable record of what was lost.
        self.assertIn(removed_pk, change.prechange_data['aggregate_routes'])
        self.assertIn(removed_pk, change.prechange_data['networks'])
        self.assertNotIn(removed_pk, change.postchange_data['aggregate_routes'])
        self.assertNotIn(removed_pk, change.postchange_data['networks'])
        self.assertIn(kept_pk, change.postchange_data['aggregate_routes'])


class BGPPasswordChangeLogTestCase(BaseTestData, TestCase):
    """
    The BGP MD5 key is change-logged like any other field.

    It is deliberately not stripped: the key is readable over REST, GraphQL and the UI
    because config generation needs it, so hiding it from the change log alone would be
    inconsistent without being safer. These tests pin that decision down, so a future
    change back to stripping is a visible, deliberate act rather than a silent one.

    The mitigation is documented in the README: store the platform's hashed or encrypted
    form rather than the raw secret.
    """

    SECRET = 'SUPERSECRET-MD5'
    ROTATED = 'ROTATED-MD5'

    @classmethod
    def setUpTestData(cls):
        cls.build_topology()
        cls.router = BGPRouter.objects.create(device=cls.devices[0], vrf=cls.vrfs[0])
        cls.user = User.objects.create_user(username='changelog-probe')

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
        return (('BGPPeer', self.peer), ('BGPPeergroup', self.peergroup))

    def test_serialize_object_includes_the_password(self):
        for label, instance in self.subjects():
            with self.subTest(model=label):
                data = instance.serialize_object()
                self.assertIn('password', data)
                self.assertEqual(data['password'], self.SECRET)

    def test_update_objectchange_records_both_snapshots(self):
        for label, instance in self.subjects():
            with self.subTest(model=label):
                instance.snapshot()
                instance.password = self.ROTATED
                change = instance.to_objectchange(ObjectChangeActionChoices.ACTION_UPDATE)

                self.assertEqual(change.prechange_data['password'], self.SECRET)
                self.assertEqual(change.postchange_data['password'], self.ROTATED)

    def test_ordinary_change_logging_still_works(self):
        for label, instance in self.subjects():
            with self.subTest(model=label):
                instance.snapshot()
                instance.description = f'{label} updated'
                instance.bfd = not instance.bfd
                change = instance.to_objectchange(ObjectChangeActionChoices.ACTION_UPDATE)

                self.assertEqual(change.prechange_data['description'], '')
                self.assertEqual(change.postchange_data['description'], f'{label} updated')
                self.assertNotEqual(change.prechange_data['bfd'], change.postchange_data['bfd'])
                self.assertEqual(change.postchange_data['remote_as'], self.asns[0].pk)

    def test_diff_reports_a_rotated_password(self):
        for label, instance in self.subjects():
            with self.subTest(model=label):
                instance.snapshot()
                instance.password = self.ROTATED
                change = instance.to_objectchange(ObjectChangeActionChoices.ACTION_UPDATE)
                change.user = self.user
                # request_id is non-null and is normally stamped by the change-logging
                # middleware; there is no request here, so supply one.
                change.request_id = uuid.uuid4()
                change.save()

                diff = ObjectChange.objects.get(pk=change.pk).diff()
                self.assertEqual(diff['pre']['password'], self.SECRET)
                self.assertEqual(diff['post']['password'], self.ROTATED)


class ConstraintNamingTestCase(TestCase):
    """
    PostgreSQL truncates identifiers at 63 bytes *silently*. A longer constraint name is
    therefore stored under a different name than the one Django holds in its migration
    state, and the two only disagree once something tries to drop or alter it.
    """

    MAX_IDENTIFIER_LENGTH = 63

    def test_every_constraint_name_fits_postgresql(self):
        for model in apps.get_app_config('netbox_routing_protocols').get_models():
            for constraint in model._meta.constraints:
                with self.subTest(model=model.__name__, constraint=constraint.name):
                    self.assertLessEqual(
                        len(constraint.name),
                        self.MAX_IDENTIFIER_LENGTH,
                        f'{constraint.name} is {len(constraint.name)} characters',
                    )

    def test_every_index_name_fits_postgresql(self):
        for model in apps.get_app_config('netbox_routing_protocols').get_models():
            for index in model._meta.indexes:
                with self.subTest(model=model.__name__, index=index.name):
                    self.assertLessEqual(len(index.name), self.MAX_IDENTIFIER_LENGTH)

    def test_constraint_names_are_unique_across_the_plugin(self):
        """Constraint names share one namespace per database, not one per table."""
        names = [
            constraint.name
            for model in apps.get_app_config('netbox_routing_protocols').get_models()
            for constraint in model._meta.constraints
        ]
        self.assertEqual(len(names), len(set(names)), 'duplicate constraint names')


class PrefixDeletionTestCase(BaseTestData, TestCase):
    """
    What happens to routing objects when the prefixes they point at go away.

    Two distinct behaviours, and conflating them is the trap:

    * A direct foreign key to a Prefix is declared ``on_delete=CASCADE``, so
      deleting exactly that prefix deletes the referencing rows.
    * NetBox's prefix hierarchy is *computed* from the CIDR values, not stored as
      a relation. Deleting a container prefix therefore deletes only that row;
      more specific prefixes and anything referencing them are untouched.
    """

    @classmethod
    def setUpTestData(cls):
        cls.build_topology()
        cls.prefix_list = PrefixList.objects.create(
            name='PL-1',
            device=cls.devices[0],
            address_family=AddressFamilyChoices.FAMILY_IPV4,
        )

    def test_prefix_foreign_keys_cascade(self):
        """Declared behaviour, asserted directly rather than inferred from a delete."""
        for model, field_name in (
            (StaticRoute, 'prefix'),
            (PrefixListRule, 'prefix'),
        ):
            with self.subTest(model=model.__name__):
                field = model._meta.get_field(field_name)
                self.assertIs(field.remote_field.on_delete, models.CASCADE)

    def test_deleting_the_referenced_prefix_deletes_the_static_route(self):
        route = StaticRoute.objects.create(
            device=self.devices[0],
            vrf=self.vrfs[0],
            prefix=self.prefixes4[0],
            nexthop=self.addresses4[0],
        )
        self.prefixes4[0].delete()
        self.assertFalse(StaticRoute.objects.filter(pk=route.pk).exists())

    def test_deleting_the_referenced_prefix_deletes_the_prefix_list_rule(self):
        rule = PrefixListRule.objects.create(
            prefix_list=self.prefix_list,
            sequence=10,
            action=ActionChoices.ACTION_PERMIT,
            prefix=self.prefixes4[0],
        )
        self.prefixes4[0].delete()
        self.assertFalse(PrefixListRule.objects.filter(pk=rule.pk).exists())

    def test_deleting_a_container_prefix_leaves_children_and_references_intact(self):
        """
        10.123.0.0/16 contains 10.123.1.0/24, but that containment is derived at
        query time. Removing the container must not take the child — or anything
        pointing at the child — with it.
        """
        child = self.prefixes4[0]
        self.assertEqual(str(child.prefix), '10.123.1.0/24')
        self.assertIn(child, Prefix.objects.filter(prefix__net_contained=str(self.container4.prefix)))

        route = StaticRoute.objects.create(
            device=self.devices[0],
            vrf=self.vrfs[0],
            prefix=child,
            nexthop=self.addresses4[0],
        )
        rule = PrefixListRule.objects.create(
            prefix_list=self.prefix_list,
            sequence=10,
            action=ActionChoices.ACTION_PERMIT,
            prefix=child,
        )

        self.container4.delete()

        self.assertTrue(Prefix.objects.filter(pk=child.pk).exists())
        self.assertTrue(StaticRoute.objects.filter(pk=route.pk).exists())
        self.assertTrue(PrefixListRule.objects.filter(pk=rule.pk).exists())
        route.refresh_from_db()
        self.assertEqual(route.prefix, child)

    def test_deleting_a_container_prefix_leaves_bgp_statements_intact(self):
        family = BGPAddressFamily.objects.create(
            bgprouter=BGPRouter.objects.create(device=self.devices[0], vrf=self.vrfs[0]),
            family=BGPAddressFamilyChoices.AFI_IPV4_UNICAST,
        )
        child = self.prefixes4[0]
        family.networks.set([child])

        self.container4.delete()

        family.refresh_from_db()
        self.assertEqual(list(family.networks.all()), [child])

    def test_deleting_a_more_specific_prefix_leaves_the_container_intact(self):
        """The cascade runs in one direction only; the parent is not swept up."""
        extra = create_prefixes('10.123.1.128/25')[0]
        route = StaticRoute.objects.create(
            device=self.devices[0],
            vrf=self.vrfs[0],
            prefix=extra,
            nexthop=self.addresses4[0],
        )

        extra.delete()

        self.assertFalse(StaticRoute.objects.filter(pk=route.pk).exists())
        self.assertTrue(Prefix.objects.filter(pk=self.container4.pk).exists())
        self.assertTrue(Prefix.objects.filter(pk=self.prefixes4[0].pk).exists())
