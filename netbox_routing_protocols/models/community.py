import re

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.db.models.constraints import UniqueConstraint

from netbox.models import PrimaryModel

from netbox_routing_protocols.choices import ActionChoices, BGPCommunityTypeChoices

__all__ = ('BGPCommunity', 'BGPCommunityList', 'BGPCommunityListRule')

# Well-known standard communities, accepted by name (RFC 1997 plus the
# ubiquitous vendor spellings).
WELL_KNOWN_COMMUNITIES = ('no-export', 'no-advertise', 'internet', 'local-AS')

STANDARD_COMMUNITY = re.compile(r'^(\d{1,5}):(\d{1,5})$')
EXTENDED_COMMUNITY = re.compile(r'^(rt|soo):(\d{1,10}):(\d{1,10})$')
LARGE_COMMUNITY = re.compile(r'^(\d{1,10}):(\d{1,10}):(\d{1,10})$')


class BGPCommunity(PrimaryModel):
    """
    A single BGP community value.

    Communities are estate-wide values — the same NO-EXPORT-TO-TRANSIT tag means
    the same thing on every router — so the community itself is a global object.
    The list, which is what gets applied on a device, carries the scoping.
    """

    value = models.CharField(
        max_length=60,
        help_text=(
            'Standard: ASN:NN or a well-known name (no-export, no-advertise, internet, local-AS). '
            'Extended: rt:ASN:NN or soo:ASN:NN. Large: ASN:NN:NN.'
        ),
    )

    type = models.CharField(
        max_length=10,
        choices=BGPCommunityTypeChoices,
        default=BGPCommunityTypeChoices.TYPE_STANDARD,
    )

    name = models.CharField(
        max_length=100,
        blank=True,
        help_text='Optional friendly name, e.g. NO-EXPORT-TO-TRANSIT.',
    )

    class Meta:
        ordering = ('value',)
        verbose_name = 'BGP Community'
        verbose_name_plural = 'BGP Communities'
        constraints = (
            UniqueConstraint(
                fields=('value',),
                name='%(app_label)s_%(class)s_unique_value',
                violation_error_message='A BGP community with this value already exists.',
            ),
        )

    def __str__(self):
        if self.name:
            return f'{self.value} ({self.name})'
        return self.value

    def clean(self):
        super().clean()

        if not self.value:
            return

        if self.type == BGPCommunityTypeChoices.TYPE_STANDARD:
            if self.value in WELL_KNOWN_COMMUNITIES:
                return
            match = STANDARD_COMMUNITY.match(self.value)
            if not match or any(int(part) > 65535 for part in match.groups()):
                raise ValidationError(
                    {
                        'value': (
                            'Standard communities are ASN:NN with each part 0-65535, '
                            'or one of: ' + ', '.join(WELL_KNOWN_COMMUNITIES) + '.'
                        ),
                    }
                )
        elif self.type == BGPCommunityTypeChoices.TYPE_EXTENDED:
            match = EXTENDED_COMMUNITY.match(self.value)
            if not match or any(int(part) > 4294967295 for part in match.groups()[1:]):
                raise ValidationError(
                    {
                        'value': ('Extended communities are rt:ASN:NN or soo:ASN:NN with each number 0-4294967295.'),
                    }
                )
        elif self.type == BGPCommunityTypeChoices.TYPE_LARGE:
            match = LARGE_COMMUNITY.match(self.value)
            if not match or any(int(part) > 4294967295 for part in match.groups()):
                raise ValidationError(
                    {
                        'value': ('Large communities are ASN:NN:NN with each part 0-4294967295.'),
                    }
                )


class BGPCommunityList(PrimaryModel):
    """
    A named, sequenced list of community match rules.

    Scoped to a device, or shared: a null device marks a fleet-wide list, the
    same pattern as prefix lists and route maps.
    """

    name = models.CharField(max_length=255)

    device = models.ForeignKey(
        to='dcim.Device',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='%(app_label)s_community_lists',
        help_text='Scope the community list to one device, or leave blank to share it fleet-wide.',
    )

    class Meta:
        ordering = ('device', 'name')
        verbose_name = 'BGP Community List'
        verbose_name_plural = 'BGP Community Lists'
        constraints = (
            # Same pairing as PrefixList and RouteMap: the plain constraint covers
            # device-scoped rows, the partial one covers shared rows on PostgreSQL 14.
            UniqueConstraint(
                fields=('device', 'name'),
                name='%(app_label)s_%(class)s_unique_name',
                violation_error_message='A community list with this name already exists on this device.',
            ),
            UniqueConstraint(
                fields=('name',),
                condition=Q(device__isnull=True),
                name='%(app_label)s_%(class)s_unique_shared_name',
                violation_error_message='A shared community list with this name already exists.',
            ),
        )

    def __str__(self):
        return self.name


class BGPCommunityListRule(PrimaryModel):
    """
    A single sequenced permit/deny entry within a community list.

    Modelled as a rule child rather than a bare M2M because that is what the
    construct is on every platform — `bgp community-list standard NAME seq 5
    permit 65001:100` — and it matches the PrefixList/PrefixListRule shape.
    """

    community_list = models.ForeignKey(
        to='netbox_routing_protocols.BGPCommunityList',
        on_delete=models.CASCADE,
        related_name='rules',
        verbose_name='Community List',
    )

    sequence = models.PositiveSmallIntegerField()

    action = models.CharField(max_length=6, choices=ActionChoices)

    community = models.ForeignKey(
        to='netbox_routing_protocols.BGPCommunity',
        on_delete=models.PROTECT,
        related_name='community_list_rules',
    )

    class Meta:
        ordering = ('community_list', 'sequence')
        verbose_name = 'BGP Community List Rule'
        verbose_name_plural = 'BGP Community List Rules'
        constraints = (
            # Spelled out rather than interpolated from %(class)s: PostgreSQL truncates
            # identifiers at 63 characters, and the interpolated name would exceed it.
            UniqueConstraint(
                fields=('community_list', 'sequence'),
                name='netbox_routing_protocols_bgp_community_rule_unique_sequence',
                violation_error_message='This sequence number is already used in this community list.',
            ),
        )

    def __str__(self):
        return f'{self.community_list.name} {self.sequence}'

    @property
    def name(self) -> str:
        return f'{self.community_list.name} {self.sequence}'
