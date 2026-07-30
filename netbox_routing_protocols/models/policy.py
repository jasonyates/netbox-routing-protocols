from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.db.models.constraints import CheckConstraint, UniqueConstraint

from netbox.models import PrimaryModel

from netbox_routing_protocols.choices import ActionChoices, AddressFamilyChoices

__all__ = ('PrefixList', 'PrefixListRule', 'RouteMap', 'RouteMapRule')

# Longest possible prefix length per address family, keyed by AddressFamilyChoices value.
MAX_PREFIX_LENGTH = {
    AddressFamilyChoices.FAMILY_IPV4: 32,
    AddressFamilyChoices.FAMILY_IPV6: 128,
}


class PrefixList(PrimaryModel):
    """
    A named, ordered list of prefix match rules.

    Scoped to a device, or shared: a null device marks a fleet-wide list that any
    device may reference, so one definition serves every leaf that carries it.
    """

    name = models.CharField(max_length=255)

    device = models.ForeignKey(
        to='dcim.Device',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='%(app_label)s_prefix_lists',
        help_text='Scope the prefix list to one device, or leave blank to share it fleet-wide.',
    )

    address_family = models.IntegerField(
        choices=AddressFamilyChoices,
        verbose_name='Address Family',
    )

    class Meta:
        ordering = ('device', 'name')
        verbose_name = 'Prefix List'
        verbose_name_plural = 'Prefix Lists'
        constraints = (
            # Only bites when device is populated: SQL treats NULLs as distinct, and
            # NULLS NOT DISTINCT needs PostgreSQL 15 while NetBox supports 14. The
            # partial constraint below covers the shared (device IS NULL) rows.
            UniqueConstraint(
                fields=('device', 'name'),
                name='%(app_label)s_%(class)s_unique_name',
                violation_error_message='A prefix list with this name already exists on this device.',
            ),
            UniqueConstraint(
                fields=('name',),
                condition=Q(device__isnull=True),
                name='%(app_label)s_%(class)s_unique_shared_name',
                violation_error_message='A shared prefix list with this name already exists.',
            ),
        )

    def __str__(self):
        return self.name


class PrefixListRule(PrimaryModel):
    """
    A single sequenced rule within a prefix list.

    Exactly one match type applies: a specific prefix, the default route, or any
    prefix. This is enforced both here and by a database constraint.
    """

    prefix_list = models.ForeignKey(
        to='netbox_routing_protocols.PrefixList',
        on_delete=models.CASCADE,
        related_name='rules',
        verbose_name='Prefix List',
    )

    sequence = models.PositiveSmallIntegerField()

    action = models.CharField(max_length=6, choices=ActionChoices)

    prefix = models.ForeignKey(
        to='ipam.Prefix',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='%(app_label)s_prefix_list_rules',
    )

    match_default = models.BooleanField(
        default=False,
        verbose_name='Match Default',
        help_text='Match the default route, 0.0.0.0/0 or ::/0.',
    )

    match_any = models.BooleanField(
        default=False,
        verbose_name='Match Any',
        help_text='Match any prefix.',
    )

    min_prefix_length = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name='Minimum Prefix Length',
        validators=[MinValueValidator(1), MaxValueValidator(128)],
        help_text='Match prefixes no shorter than this length (ge).',
    )

    max_prefix_length = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name='Maximum Prefix Length',
        validators=[MinValueValidator(1), MaxValueValidator(128)],
        help_text='Match prefixes no longer than this length (le).',
    )

    class Meta:
        ordering = ('prefix_list', 'sequence')
        verbose_name = 'Prefix List Rule'
        verbose_name_plural = 'Prefix List Rules'
        constraints = (
            UniqueConstraint(
                fields=('prefix_list', 'sequence'),
                name='%(app_label)s_%(class)s_unique_sequence',
                violation_error_message='This sequence number is already used in this prefix list.',
            ),
            CheckConstraint(
                condition=(
                    Q(match_default=True, match_any=False, prefix__isnull=True)
                    | Q(match_default=False, match_any=True, prefix__isnull=True)
                    | Q(match_default=False, match_any=False, prefix__isnull=False)
                ),
                name='%(app_label)s_%(class)s_single_match_type',
                violation_error_message=('Set exactly one of Prefix, Match Default or Match Any.'),
            ),
        )

    def __str__(self):
        return f'{self.prefix_list.name} {self.sequence}'

    @property
    def name(self) -> str:
        return f'{self.prefix_list.name} {self.sequence}'

    def clean(self):
        super().clean()

        if self.prefix and self.prefix_list_id:
            if self.prefix.family != self.prefix_list.address_family:
                raise ValidationError(
                    {
                        'prefix': (
                            f'Prefix {self.prefix.prefix} is not in address family '
                            f'IPv{self.prefix_list.address_family}.'
                        ),
                    }
                )

        # Equality is legal, and idiomatic: "ge 24 le 24" is how every mainstream
        # platform spells "exactly a /24". Only an inverted range is an error.
        if self.min_prefix_length and self.max_prefix_length:
            if self.min_prefix_length > self.max_prefix_length:
                raise ValidationError(
                    {
                        'max_prefix_length': ('Maximum prefix length cannot be less than the minimum prefix length.'),
                    }
                )

        # Bound the lengths to the list's address family rather than a flat 128.
        if self.prefix_list_id:
            limit = MAX_PREFIX_LENGTH.get(self.prefix_list.address_family)
            for field in ('min_prefix_length', 'max_prefix_length'):
                value = getattr(self, field)
                if limit and value and value > limit:
                    raise ValidationError(
                        {
                            field: (f'Cannot exceed {limit} for an IPv{self.prefix_list.address_family} prefix list.'),
                        }
                    )


class RouteMap(PrimaryModel):
    """
    A named, ordered set of route map rules.

    Scoped to a device, or shared: a null device marks a fleet-wide route map that
    any device may reference.
    """

    name = models.CharField(max_length=255)

    device = models.ForeignKey(
        to='dcim.Device',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='%(app_label)s_route_maps',
        help_text='Scope the route map to one device, or leave blank to share it fleet-wide.',
    )

    class Meta:
        ordering = ('device', 'name')
        verbose_name = 'Route Map'
        verbose_name_plural = 'Route Maps'
        constraints = (
            # Same pairing as PrefixList: the plain constraint covers device-scoped
            # rows, the partial one covers shared rows on PostgreSQL 14.
            UniqueConstraint(
                fields=('device', 'name'),
                name='%(app_label)s_%(class)s_unique_name',
                violation_error_message='A route map with this name already exists on this device.',
            ),
            UniqueConstraint(
                fields=('name',),
                condition=Q(device__isnull=True),
                name='%(app_label)s_%(class)s_unique_shared_name',
                violation_error_message='A shared route map with this name already exists.',
            ),
        )

    def __str__(self):
        return self.name


class RouteMapRule(PrimaryModel):
    """
    A single sequenced rule within a route map.

    Either it matches a prefix list, or it matches anything — never both.
    """

    route_map = models.ForeignKey(
        to='netbox_routing_protocols.RouteMap',
        on_delete=models.CASCADE,
        related_name='rules',
        verbose_name='Route Map',
    )

    sequence = models.PositiveSmallIntegerField()

    action = models.CharField(max_length=6, choices=ActionChoices)

    prefix_list = models.ForeignKey(
        to='netbox_routing_protocols.PrefixList',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name='route_map_rules',
        verbose_name='Match Prefix List',
    )

    match_any = models.BooleanField(
        default=False,
        verbose_name='Match Any',
        help_text="Match anything, e.g. 'route-map RM-EXAMPLE deny 9999'.",
    )

    class Meta:
        ordering = ('route_map', 'sequence')
        verbose_name = 'Route Map Rule'
        verbose_name_plural = 'Route Map Rules'
        constraints = (
            UniqueConstraint(
                fields=('route_map', 'sequence'),
                name='%(app_label)s_%(class)s_unique_sequence',
                violation_error_message='This sequence number is already used in this route map.',
            ),
            CheckConstraint(
                condition=(Q(match_any=False, prefix_list__isnull=False) | Q(match_any=True, prefix_list__isnull=True)),
                name='%(app_label)s_%(class)s_single_match_type',
                violation_error_message='Set exactly one of Prefix List or Match Any.',
            ),
        )

    def __str__(self):
        return f'{self.route_map.name} {self.sequence}'

    @property
    def name(self) -> str:
        return f'{self.route_map.name} {self.sequence}'

    def clean(self):
        super().clean()

        if self.prefix_list_id and self.route_map_id and self.prefix_list.device_id:
            # A shared prefix list (no device) may be referenced from anywhere. A
            # device-scoped one may only be referenced from a route map on the same
            # device — and never from a shared route map, which renders on every
            # device while the list exists on just one.
            if self.route_map.device_id is None:
                raise ValidationError(
                    {
                        'prefix_list': (
                            f'Shared route map {self.route_map.name} cannot reference prefix list '
                            f'{self.prefix_list.name}, which is scoped to a single device.'
                        ),
                    }
                )
            if self.prefix_list.device_id != self.route_map.device_id:
                raise ValidationError(
                    {
                        'prefix_list': (
                            f'Prefix list {self.prefix_list.name} belongs to a different device '
                            f'than route map {self.route_map.name}.'
                        ),
                    }
                )
