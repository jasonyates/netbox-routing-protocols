"""
Shared fixture helpers for the plugin's test suite.

Everything in this plugin hangs off DCIM and IPAM objects, so the individual test
modules would otherwise repeat the same twenty lines of scaffolding. The helpers
below build that scaffolding once; ``BaseTestData.build_topology()`` assembles the
standard topology as class attributes for use from ``setUpTestData()``.

Two details that fixtures must respect:

* ``PrefixList`` and ``RouteMap`` gain a terminating ``deny 9999 match_any`` rule
  from a ``post_save`` receiver, so any count of rules has to allow for it. Use
  ``PLUGINS_CONFIG_NO_DEFAULT_DENY`` with ``override_settings`` to switch that off.
* Prefixes are created one at a time rather than with ``bulk_create()`` so that
  NetBox's own ``save()`` logic runs and the prefix hierarchy is consistent.
"""

from dcim.choices import InterfaceTypeChoices
from dcim.models import Interface, Site
from ipam.models import ASN, RIR, VRF, IPAddress, Prefix
from utilities.testing import create_test_device

__all__ = (
    'BaseTestData',
    'PLUGINS_CONFIG_NO_DEFAULT_DENY',
    'create_asns',
    'create_devices',
    'create_interfaces',
    'create_ip_addresses',
    'create_prefixes',
    'create_vrfs',
)

# PLUGINS_CONFIG value that disables the terminating deny-9999 receiver. Pass to
# django.test.override_settings; get_plugin_config() reads settings.PLUGINS_CONFIG
# directly, so replacing the whole mapping is enough.
PLUGINS_CONFIG_NO_DEFAULT_DENY = {'netbox_routing_protocols': {'create_default_deny_rule': False}}


def create_devices(*names, site=None):
    """Create a Device per name, all in the same site."""
    if site is None:
        site, _ = Site.objects.get_or_create(name='Site 1', slug='site-1')
    return [create_test_device(name, site=site) for name in names]


def create_interfaces(device, *names, vrf=None):
    """Create interfaces on a device, optionally within a VRF."""
    return [
        Interface.objects.create(
            device=device,
            name=name,
            type=InterfaceTypeChoices.TYPE_1GE_FIXED,
            vrf=vrf,
        )
        for name in names
    ]


def create_vrfs(*names):
    return [VRF.objects.create(name=name) for name in names]


def create_asns(*numbers, rir=None):
    if rir is None:
        rir, _ = RIR.objects.get_or_create(name='RFC 6996', slug='rfc-6996', defaults={'is_private': True})
    return [ASN.objects.create(asn=number, rir=rir) for number in numbers]


def create_prefixes(*values, vrf=None):
    """Create prefixes individually so NetBox's Prefix.save() runs for each."""
    return [Prefix.objects.create(prefix=value, vrf=vrf) for value in values]


def create_ip_addresses(*values, vrf=None, assigned_object=None):
    addresses = []
    for value in values:
        address = IPAddress(address=value, vrf=vrf)
        if assigned_object is not None:
            address.assigned_object = assigned_object
        address.save()
        addresses.append(address)
    return addresses


class BaseTestData:
    """
    Mixin providing the DCIM and IPAM objects every test module needs.

    Call ``cls.build_topology()`` from ``setUpTestData()``. It sets:

    ``devices``       two devices, ``core-sw1`` and ``core-sw2``
    ``interfaces1/2`` four interfaces on each device, in ``vrfs[0]``
    ``vrfs``          three VRFs
    ``asns``          four ASNs
    ``container4``    10.123.0.0/16, the parent of every IPv4 prefix below
    ``prefixes4``     10.123.1.0/24 through 10.123.8.0/24
    ``container6``    2001:db8::/32
    ``prefixes6``     2001:db8:1::/48 through 2001:db8:3::/48
    ``addresses4``    10.123.1.1/24 through 10.123.1.8/24
    ``addresses6``    2001:db8:1::1/64 through 2001:db8:1::3/64

    The device names deliberately contain the substring ``core`` so free-text
    search can be exercised against something meaningful.
    """

    @classmethod
    def build_topology(cls):
        cls.devices = create_devices('core-sw1', 'core-sw2')
        cls.vrfs = create_vrfs('VRF 1', 'VRF 2', 'VRF 3')
        cls.interfaces1 = create_interfaces(
            cls.devices[0], 'Ethernet1', 'Ethernet2', 'Ethernet3', 'Ethernet4', vrf=cls.vrfs[0]
        )
        cls.interfaces2 = create_interfaces(
            cls.devices[1], 'Ethernet1', 'Ethernet2', 'Ethernet3', 'Ethernet4', vrf=cls.vrfs[0]
        )
        cls.asns = create_asns(65000, 65001, 65002, 65003)

        cls.container4 = create_prefixes('10.123.0.0/16')[0]
        cls.prefixes4 = create_prefixes(*[f'10.123.{i}.0/24' for i in range(1, 9)])
        cls.container6 = create_prefixes('2001:db8::/32')[0]
        cls.prefixes6 = create_prefixes(*[f'2001:db8:{i}::/48' for i in range(1, 4)])

        cls.addresses4 = create_ip_addresses(*[f'10.123.1.{i}/24' for i in range(1, 9)])
        cls.addresses6 = create_ip_addresses(*[f'2001:db8:1::{i}/64' for i in range(1, 4)])
