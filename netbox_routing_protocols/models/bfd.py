from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q
from django.db.models.constraints import UniqueConstraint

from netbox.models import PrimaryModel

__all__ = ('BFDProfile',)


class BFDProfile(PrimaryModel):
    """
    A named set of BFD session parameters.

    Referenced by BGP peers and peer groups today, and by any protocol added
    later (OSPF interfaces, static routes) — which is why it is its own model
    rather than fields on the BGP session. Scoped to a device, or shared: BFD
    profiles are in practice identical fleet-wide, so a null device (the common
    case) marks a profile any device may reference.

    Renderers emit a named template block on platforms that have one (FRR
    ``bfd profile``, IOS-XE ``bfd-template``) and inline the intervals at each
    attachment point on platforms that do not (EOS).
    """

    name = models.CharField(max_length=100)

    device = models.ForeignKey(
        to='dcim.Device',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='%(app_label)s_bfd_profiles',
        help_text='Scope the profile to one device, or leave blank to share it fleet-wide.',
    )

    # Interval fields are milliseconds. All are optional: a null means the
    # platform default (300 ms intervals, multiplier 3 on FRR).
    min_tx = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Minimum TX Interval',
        validators=[MinValueValidator(1), MaxValueValidator(60000)],
        help_text='Minimum transmit interval in milliseconds.',
    )

    min_rx = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Minimum RX Interval',
        validators=[MinValueValidator(1), MaxValueValidator(60000)],
        help_text='Minimum receive interval in milliseconds.',
    )

    detect_multiplier = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name='Detect Multiplier',
        validators=[MinValueValidator(1), MaxValueValidator(255)],
        help_text='Number of missed packets before the session is declared down. Platform default is 3.',
    )

    echo_mode = models.BooleanField(
        default=False,
        verbose_name='Echo Mode',
        help_text='Use echo packets to test the forwarding path.',
    )

    echo_tx = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Echo TX Interval',
        validators=[MinValueValidator(1), MaxValueValidator(60000)],
        help_text='Echo transmit interval in milliseconds.',
    )

    echo_rx = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Echo RX Interval',
        validators=[MinValueValidator(1), MaxValueValidator(60000)],
        help_text='Echo receive interval in milliseconds.',
    )

    passive_mode = models.BooleanField(
        default=False,
        verbose_name='Passive Mode',
        help_text='Wait for the peer to initiate the BFD session.',
    )

    minimum_ttl = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        verbose_name='Minimum TTL',
        validators=[MinValueValidator(1), MaxValueValidator(254)],
        help_text='Only accept BFD packets with at least this TTL (multihop sessions).',
    )

    class Meta:
        ordering = ('device', 'name')
        verbose_name = 'BFD Profile'
        verbose_name_plural = 'BFD Profiles'
        constraints = (
            # Same pairing as PrefixList and RouteMap: the plain constraint covers
            # device-scoped rows, the partial one covers shared rows on PostgreSQL 14.
            UniqueConstraint(
                fields=('device', 'name'),
                name='%(app_label)s_%(class)s_unique_name',
                violation_error_message='A BFD profile with this name already exists on this device.',
            ),
            UniqueConstraint(
                fields=('name',),
                condition=Q(device__isnull=True),
                name='%(app_label)s_%(class)s_unique_shared_name',
                violation_error_message='A shared BFD profile with this name already exists.',
            ),
        )

    def __str__(self):
        return self.name

    def clean(self):
        super().clean()

        for field in ('echo_tx', 'echo_rx'):
            if getattr(self, field) and not self.echo_mode:
                raise ValidationError(
                    {
                        field: 'Echo intervals require Echo Mode to be enabled.',
                    }
                )
