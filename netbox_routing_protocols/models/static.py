from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.constraints import CheckConstraint, UniqueConstraint

from netbox.models import PrimaryModel

__all__ = ('StaticRoute',)


class StaticRoute(PrimaryModel):
    """A static route installed on a device, optionally within a VRF."""

    device = models.ForeignKey(
        to='dcim.Device',
        on_delete=models.CASCADE,
        related_name='%(app_label)s_static_routes',
    )

    vrf = models.ForeignKey(
        to='ipam.VRF',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='%(app_label)s_static_routes',
        verbose_name='VRF',
    )

    prefix = models.ForeignKey(
        to='ipam.Prefix',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='%(app_label)s_static_routes',
        help_text='Destination prefix. Leave empty and tick Default Route for 0.0.0.0/0 or ::/0.',
    )

    # Required: a static route with no next hop cannot be rendered or configured,
    # and the default-route naming below depends on the next hop's address family.
    nexthop = models.ForeignKey(
        to='ipam.IPAddress',
        on_delete=models.CASCADE,
        related_name='%(app_label)s_static_routes',
        verbose_name='Next Hop',
    )

    default_route = models.BooleanField(
        default=False,
        verbose_name='Default Route',
        help_text='Route the default destination, 0.0.0.0/0 or ::/0.',
    )

    class Meta:
        ordering = ('device', 'prefix')
        verbose_name = 'Static Route'
        verbose_name_plural = 'Static Routes'
        constraints = (
            # Exactly one of "a prefix" or "the default route".
            CheckConstraint(
                condition=(Q(default_route=True, prefix__isnull=True) | Q(default_route=False, prefix__isnull=False)),
                name='%(app_label)s_%(class)s_prefix_or_default',
                violation_error_message=('Set either a Prefix or Default Route, but not both and not neither.'),
            ),
            # These two only bite when vrf is populated: SQL treats NULLs as distinct,
            # and NULLS NOT DISTINCT needs PostgreSQL 15 while NetBox supports 14.
            UniqueConstraint(
                fields=('device', 'vrf', 'prefix'),
                name='%(app_label)s_%(class)s_unique_prefix',
                violation_error_message=('A static route for this prefix already exists on this device and VRF.'),
            ),
            UniqueConstraint(
                fields=('device', 'vrf', 'nexthop'),
                condition=Q(default_route=True),
                name='%(app_label)s_%(class)s_unique_default',
                violation_error_message=('A default route to this next hop already exists on this device and VRF.'),
            ),
            # ...and these two cover the global routing table. A partial index over the
            # rows where vrf IS NULL needs no NULLS NOT DISTINCT, so it works on
            # PostgreSQL 14. Enforcing it in the database rather than in clean() is what
            # makes it safe: two concurrent API writes would both pass a Python
            # existence check and both commit.
            UniqueConstraint(
                fields=('device', 'prefix'),
                condition=Q(vrf__isnull=True),
                name='%(app_label)s_%(class)s_unique_global_prefix',
                violation_error_message=(
                    'A static route for this prefix already exists on this device in the global routing table.'
                ),
            ),
            UniqueConstraint(
                fields=('device', 'nexthop'),
                condition=Q(vrf__isnull=True, default_route=True),
                name='%(app_label)s_%(class)s_unique_global_default',
                violation_error_message=(
                    'A default route to this next hop already exists on this device in the global routing table.'
                ),
            ),
        )

    def __str__(self):
        return self.name

    @property
    def name(self) -> str:
        if self.prefix_id:
            return str(self.prefix.prefix)
        # Guarded rather than assumed: nexthop is required, but the property is
        # reachable from an unsaved instance during form validation.
        if self.nexthop_id and self.nexthop.family == 6:
            return '::/0'
        return '0.0.0.0/0'

    def clean(self):
        super().clean()

        if self.prefix and self.nexthop and self.prefix.family != self.nexthop.family:
            raise ValidationError(
                {
                    'nexthop': (
                        f'Next hop {self.nexthop.address} is not in the same address family '
                        f'as prefix {self.prefix.prefix}.'
                    ),
                }
            )

        # Duplicates in the global routing table used to be caught here with a
        # SELECT-then-INSERT, which two concurrent writers could both pass. They are now
        # partial unique constraints; full_clean() surfaces them through
        # validate_constraints() with the messages declared in Meta.
