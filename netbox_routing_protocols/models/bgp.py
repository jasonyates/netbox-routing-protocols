from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.db.models.constraints import CheckConstraint, UniqueConstraint

from netbox.models import PrimaryModel

from netbox_routing_protocols.choices import (
    BGPAddressFamilyChoices,
    BGPRedistributeProtocolChoices,
)

__all__ = (
    'BGPRouter',
    'BGPPeergroup',
    'BGPPeer',
    'BGPAddressFamily',
    'BGPAddressFamilyRedistribute',
    'BGPPeerAddressFamily',
    'BGPPeergroupAddressFamily',
)


class BGPRouter(PrimaryModel):
    """
    A BGP routing instance on a device, within a VRF.

    Everything else in this module hangs off a router, which is what fixes the
    device and VRF for peers, peer groups and address families.
    """

    device = models.ForeignKey(
        to='dcim.Device',
        on_delete=models.CASCADE,
        related_name='%(app_label)s_bgp_routers',
    )

    vrf = models.ForeignKey(
        to='ipam.VRF',
        on_delete=models.PROTECT,
        related_name='%(app_label)s_bgp_routers',
        verbose_name='VRF',
    )

    enable = models.BooleanField(default=True, help_text='Enable BGP on this device and VRF.')

    asn = models.ForeignKey(
        to='ipam.ASN',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='%(app_label)s_bgp_routers',
        verbose_name='ASN',
    )

    router_id = models.ForeignKey(
        to='ipam.IPAddress',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='%(app_label)s_bgp_routers',
        verbose_name='Router ID',
    )

    # Renamed from aspath_ignore, which described the wrong feature: the field was
    # inherited from an NVUE estate, where "aspath-ignore" spells multipath-relax.
    multipath_relax = models.BooleanField(
        default=True,
        verbose_name='Multipath Relax',
        help_text=('Allow ECMP across eBGP paths from different neighbouring ASNs (bestpath as-path multipath-relax).'),
    )

    route_reflection = models.BooleanField(
        default=False,
        verbose_name='Route Reflection',
        help_text='Act as an iBGP route reflector.',
    )

    enable_evpn = models.BooleanField(
        default=False,
        verbose_name='Enable EVPN',
        help_text='Enable the EVPN L3VNI for this router, if one is configured on the VRF.',
    )

    class Meta:
        ordering = ('device', 'vrf')
        verbose_name = 'BGP Router'
        verbose_name_plural = 'BGP Routers'
        constraints = (
            UniqueConstraint(
                fields=('device', 'vrf'),
                name='%(app_label)s_%(class)s_unique_device_vrf',
                violation_error_message='A BGP router already exists for this device and VRF.',
            ),
        )

    def __str__(self):
        return f'{self.device} :: {self.vrf}'

    @property
    def name(self) -> str:
        return f'{self.device.name} :: {self.vrf.name}'

    def clean(self):
        super().clean()

        if not self.router_id_id or not self.device_id:
            return

        assigned = self.router_id.assigned_object
        if getattr(assigned, 'device_id', None) != self.device_id:
            raise ValidationError(
                {
                    'router_id': (
                        f'Router ID {self.router_id.address} is not assigned to an interface '
                        f'on device {self.device.name}.'
                    ),
                }
            )

        if self.router_id.vrf_id != self.vrf_id:
            raise ValidationError(
                {
                    'router_id': (f'Router ID {self.router_id.address} does not belong to VRF {self.vrf.name}.'),
                }
            )


class BGPPeerAttributes(PrimaryModel):
    """Session attributes shared by individual peers and by peer groups."""

    bgprouter = models.ForeignKey(
        to='netbox_routing_protocols.BGPRouter',
        on_delete=models.CASCADE,
        related_name='%(class)ss',
        verbose_name='BGP Router',
    )

    enable = models.BooleanField(default=True)

    remote_as = models.ForeignKey(
        to='ipam.ASN',
        on_delete=models.PROTECT,
        related_name='%(app_label)s_%(class)s_peers',
        verbose_name='Remote AS',
    )

    bfd = models.BooleanField(
        default=True,
        verbose_name='BFD',
        help_text='Use Bidirectional Forwarding Detection for this session.',
    )

    # Held and returned in plaintext, like any other field: the key has to reach device
    # configuration, so automation must be able to read it back. Store your platform's
    # hashed or encrypted representation rather than the raw secret — see the README.
    password = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text='BGP MD5 authentication key. Prefer a hashed form over the raw secret.',
    )

    ebgp_multihop = models.BooleanField(
        default=False,
        verbose_name='eBGP Multihop',
        help_text='Allow the peer to be more than one hop away.',
    )

    ebgp_multihop_ttl = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name='eBGP Multihop TTL',
        validators=[MinValueValidator(1), MaxValueValidator(255)],
    )

    class Meta:
        abstract = True

    @property
    def device(self):
        return self.bgprouter.device

    @property
    def vrf(self):
        return self.bgprouter.vrf

    def clean(self):
        super().clean()

        if self.ebgp_multihop_ttl and not self.ebgp_multihop:
            raise ValidationError(
                {
                    'ebgp_multihop_ttl': 'Cannot set a multihop TTL unless eBGP Multihop is enabled.',
                }
            )


class BGPPeergroup(BGPPeerAttributes):
    """A group of BGP peers sharing a common set of attributes."""

    name = models.CharField(max_length=255)

    class Meta:
        ordering = ('bgprouter', 'name')
        verbose_name = 'BGP Peer Group'
        verbose_name_plural = 'BGP Peer Groups'
        constraints = (
            UniqueConstraint(
                fields=('bgprouter', 'name'),
                name='%(app_label)s_%(class)s_unique_name',
                violation_error_message='A peer group with this name already exists on this BGP router.',
            ),
        )

    def __str__(self):
        return self.name


class BGPPeer(BGPPeerAttributes):
    """
    A single BGP neighbour.

    Addressed either by a remote IP address or, for unnumbered sessions, by a
    local interface — never both.
    """

    remote_address = models.ForeignKey(
        to='ipam.IPAddress',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='%(app_label)s_bgp_peers',
        verbose_name='Remote Address',
        help_text='Remote IP address of the peer.',
    )

    interface = models.ForeignKey(
        to='dcim.Interface',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='%(app_label)s_bgp_peers',
        help_text='Local interface for an unnumbered session.',
    )

    peergroup = models.ForeignKey(
        to='netbox_routing_protocols.BGPPeergroup',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='peers',
        verbose_name='Peer Group',
    )

    class Meta:
        ordering = ('bgprouter', 'interface', 'remote_address')
        verbose_name = 'BGP Peer'
        verbose_name_plural = 'BGP Peers'
        constraints = (
            CheckConstraint(
                condition=(
                    Q(remote_address__isnull=False, interface__isnull=True)
                    | Q(remote_address__isnull=True, interface__isnull=False)
                ),
                name='%(app_label)s_%(class)s_address_or_interface',
                violation_error_message='Set either a Remote Address or an Interface, not both.',
            ),
            UniqueConstraint(
                fields=('bgprouter', 'remote_address'),
                name='%(app_label)s_%(class)s_unique_address',
                violation_error_message='This peer address is already configured on this BGP router.',
            ),
            UniqueConstraint(
                fields=('bgprouter', 'interface'),
                name='%(app_label)s_%(class)s_unique_interface',
                violation_error_message='This interface is already configured on this BGP router.',
            ),
        )

    def __str__(self):
        return self.name

    @property
    def name(self) -> str:
        if self.interface_id:
            return self.interface.name
        # Guarded rather than assumed: a saved row always has one or the other under
        # the CheckConstraint, but the property is reached from unsaved instances
        # during form and serializer validation, before either has been set.
        if self.remote_address_id:
            return str(self.remote_address.address)
        return ''

    def clean(self):
        super().clean()

        if not self.bgprouter_id:
            return

        if self.interface_id:
            if self.interface.device_id != self.bgprouter.device_id:
                raise ValidationError(
                    {
                        'interface': (
                            f'Interface {self.interface.name} does not belong to device {self.bgprouter.device.name}.'
                        ),
                    }
                )
            if self.interface.vrf_id != self.bgprouter.vrf_id:
                raise ValidationError(
                    {
                        'interface': (
                            f'Interface {self.interface.name} does not belong to VRF {self.bgprouter.vrf.name}.'
                        ),
                    }
                )

        if self.peergroup_id and self.peergroup.bgprouter_id != self.bgprouter_id:
            raise ValidationError(
                {
                    'peergroup': (f'Peer group {self.peergroup.name} belongs to a different BGP router.'),
                }
            )


class BGPAddressFamily(PrimaryModel):
    """An address family enabled on a BGP router, with its origination policy."""

    bgprouter = models.ForeignKey(
        to='netbox_routing_protocols.BGPRouter',
        on_delete=models.CASCADE,
        related_name='address_families',
        verbose_name='BGP Router',
    )

    family = models.CharField(
        max_length=30,
        choices=BGPAddressFamilyChoices,
        verbose_name='Address Family',
    )

    enable = models.BooleanField(default=True)

    aggregate_routes = models.ManyToManyField(
        to='ipam.Prefix',
        blank=True,
        related_name='%(app_label)s_bgp_aggregates',
        verbose_name='Aggregate Routes',
    )

    aggregate_route_map = models.ForeignKey(
        to='netbox_routing_protocols.RouteMap',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='bgp_aggregate_families',
        verbose_name='Aggregate Route Map',
    )

    networks = models.ManyToManyField(
        to='ipam.Prefix',
        blank=True,
        related_name='%(app_label)s_bgp_networks',
        verbose_name='Network Statements',
    )

    network_route_map = models.ForeignKey(
        to='netbox_routing_protocols.RouteMap',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='bgp_network_families',
        verbose_name='Network Route Map',
    )

    export_to_evpn = models.BooleanField(
        default=False,
        verbose_name='Export to EVPN',
        help_text='Export routes to the EVPN L3VNI, if one is configured.',
    )

    class Meta:
        ordering = ('bgprouter', 'family')
        verbose_name = 'BGP Address Family'
        verbose_name_plural = 'BGP Address Families'
        constraints = (
            UniqueConstraint(
                fields=('bgprouter', 'family'),
                name='%(app_label)s_%(class)s_unique_family',
                violation_error_message='This address family is already configured on this BGP router.',
            ),
        )

    def __str__(self):
        return self.get_family_display()

    @property
    def device(self):
        return self.bgprouter.device

    @property
    def vrf(self):
        return self.bgprouter.vrf

    def clean(self):
        super().clean()

        if not self.bgprouter_id:
            return

        for field in ('aggregate_route_map', 'network_route_map'):
            route_map = getattr(self, field)
            if route_map and route_map.device_id != self.bgprouter.device_id:
                raise ValidationError(
                    {
                        field: (
                            f'Route map {route_map.name} belongs to a different device than '
                            f'BGP router {self.bgprouter}.'
                        ),
                    }
                )


class BGPAddressFamilyRedistribute(PrimaryModel):
    """Redistribution of another protocol's routes into a BGP address family."""

    family = models.ForeignKey(
        to='netbox_routing_protocols.BGPAddressFamily',
        on_delete=models.CASCADE,
        related_name='redistributions',
        verbose_name='Address Family',
    )

    protocol = models.CharField(
        max_length=20,
        choices=BGPRedistributeProtocolChoices,
    )

    enable = models.BooleanField(default=True)

    route_map = models.ForeignKey(
        to='netbox_routing_protocols.RouteMap',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='bgp_redistributions',
        verbose_name='Route Map',
    )

    class Meta:
        ordering = ('family', 'protocol')
        verbose_name = 'BGP Redistribution'
        verbose_name_plural = 'BGP Redistributions'
        constraints = (
            # Spelled out rather than interpolated from %(class)s: PostgreSQL truncates
            # identifiers at 63 characters, and
            # "netbox_routing_protocols_bgpaddressfamilyredistribute_unique_protocol" is 69,
            # which would leave Django's migration state disagreeing with the database.
            UniqueConstraint(
                fields=('family', 'protocol'),
                name='netbox_routing_protocols_bgp_redistribute_unique_protocol',
                violation_error_message='This protocol is already redistributed into this address family.',
            ),
        )

    def __str__(self):
        return f'{self.family} :: {self.get_protocol_display()}'

    @property
    def name(self) -> str:
        return str(self)

    def clean(self):
        super().clean()

        if self.route_map and self.family_id:
            if self.route_map.device_id != self.family.bgprouter.device_id:
                raise ValidationError(
                    {
                        'route_map': (f'Route map {self.route_map.name} belongs to a different device.'),
                    }
                )


class BGPSessionAddressFamilyAttributes(PrimaryModel):
    """
    Per-address-family settings shared by peer and peer-group address families.

    Peers and peer groups get their own concrete model rather than sharing one
    through a generic relation: there are exactly two owners, both known here, so
    real foreign keys buy referential integrity and a straightforward API.
    """

    family = models.CharField(
        max_length=30,
        choices=BGPAddressFamilyChoices,
        verbose_name='Address Family',
    )

    enable = models.BooleanField(default=True)

    inbound_policy = models.ForeignKey(
        to='netbox_routing_protocols.RouteMap',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='%(class)s_inbound',
        verbose_name='Inbound Policy',
    )

    outbound_policy = models.ForeignKey(
        to='netbox_routing_protocols.RouteMap',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='%(class)s_outbound',
        verbose_name='Outbound Policy',
    )

    soft_reconfiguration = models.BooleanField(
        default=True,
        verbose_name='Soft Reconfiguration',
    )

    default_originate = models.BooleanField(
        default=False,
        verbose_name='Default Originate',
        help_text='Originate a default route towards this neighbour.',
    )

    route_reflector_client = models.BooleanField(
        default=False,
        verbose_name='Route Reflector Client',
        help_text='Treat this neighbour as a route reflector client.',
    )

    class Meta:
        abstract = True

    def _validate_policy_device(self, device_id, device_name):
        for field in ('inbound_policy', 'outbound_policy'):
            route_map = getattr(self, field)
            if route_map and route_map.device_id != device_id:
                raise ValidationError(
                    {
                        field: f'Route map {route_map.name} does not belong to device {device_name}.',
                    }
                )


class BGPPeerAddressFamily(BGPSessionAddressFamilyAttributes):
    """An address family enabled on an individual BGP peer."""

    peer = models.ForeignKey(
        to='netbox_routing_protocols.BGPPeer',
        on_delete=models.CASCADE,
        related_name='address_families',
        verbose_name='BGP Peer',
    )

    class Meta:
        ordering = ('peer', 'family')
        verbose_name = 'BGP Peer Address Family'
        verbose_name_plural = 'BGP Peer Address Families'
        constraints = (
            UniqueConstraint(
                fields=('peer', 'family'),
                name='%(app_label)s_%(class)s_unique_family',
                violation_error_message='This address family is already configured on this peer.',
            ),
        )

    def __str__(self):
        return f'{self.peer} :: {self.get_family_display()}'

    @property
    def name(self) -> str:
        return str(self)

    def clean(self):
        super().clean()
        if self.peer_id:
            device = self.peer.bgprouter.device
            self._validate_policy_device(device.pk, device.name)


class BGPPeergroupAddressFamily(BGPSessionAddressFamilyAttributes):
    """An address family enabled on a BGP peer group."""

    peergroup = models.ForeignKey(
        to='netbox_routing_protocols.BGPPeergroup',
        on_delete=models.CASCADE,
        related_name='address_families',
        verbose_name='BGP Peer Group',
    )

    class Meta:
        ordering = ('peergroup', 'family')
        verbose_name = 'BGP Peer Group Address Family'
        verbose_name_plural = 'BGP Peer Group Address Families'
        constraints = (
            # Spelled out for the same reason as the redistribution constraint above:
            # "netbox_routing_protocols_bgppeergroupaddressfamily_unique_family" is 64
            # characters, one over PostgreSQL's identifier limit.
            UniqueConstraint(
                fields=('peergroup', 'family'),
                name='netbox_routing_protocols_bgp_peergroup_af_unique_family',
                violation_error_message='This address family is already configured on this peer group.',
            ),
        )

    def __str__(self):
        return f'{self.peergroup} :: {self.get_family_display()}'

    @property
    def name(self) -> str:
        return str(self)

    def clean(self):
        super().clean()
        if self.peergroup_id:
            device = self.peergroup.bgprouter.device
            self._validate_policy_device(device.pk, device.name)
