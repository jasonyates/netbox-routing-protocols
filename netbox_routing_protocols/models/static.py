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
            # These only bite when vrf is populated: SQL treats NULLs as distinct, and
            # NULLS NOT DISTINCT needs PostgreSQL 15 while NetBox supports 14. The
            # global VRF case is covered by clean() below.
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

        # Duplicate detection for routes in the global table. Routes inside a VRF are
        # covered by the unique constraints above; those skip rows where vrf IS NULL.
        if self.vrf_id is None and self.device_id:
            duplicates = StaticRoute.objects.filter(device=self.device_id, vrf__isnull=True).exclude(pk=self.pk)

            if self.default_route and self.nexthop_id:
                if duplicates.filter(default_route=True, nexthop=self.nexthop_id).exists():
                    raise ValidationError(
                        {
                            'nexthop': (
                                'A default route to this next hop already exists on this device '
                                'in the global routing table.'
                            ),
                        }
                    )
            elif self.prefix_id and duplicates.filter(prefix=self.prefix_id).exists():
                raise ValidationError(
                    {
                        'prefix': (
                            'A static route for this prefix already exists on this device in the global routing table.'
                        ),
                    }
                )
