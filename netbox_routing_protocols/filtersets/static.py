import re

import django_filters
from django.db.models import Q
from django.utils.translation import gettext as _

from dcim.models import Device
from ipam.models import VRF, IPAddress, Prefix
from netbox.filtersets import NetBoxModelFilterSet
from utilities.filtersets import register_filterset

from netbox_routing_protocols.models import StaticRoute

__all__ = ('StaticRouteFilterSet',)

# Free text is only matched against IPAM columns when it could plausibly be part of an address or
# prefix. `istartswith` is safe on NetBox's CIDR fields (it casts the column to TEXT); `contains`
# is *not* — there it means network containment and raises on non-CIDR input.
IP_LIKE = re.compile(r'^[0-9a-fA-F.:/]+$')


@register_filterset
class StaticRouteFilterSet(NetBoxModelFilterSet):
    device_id = django_filters.ModelMultipleChoiceFilter(
        field_name='device',
        queryset=Device.objects.all(),
        label=_('Device (ID)'),
    )
    device = django_filters.ModelMultipleChoiceFilter(
        field_name='device__name',
        queryset=Device.objects.all(),
        to_field_name='name',
        label=_('Device (name)'),
    )
    vrf_id = django_filters.ModelMultipleChoiceFilter(
        field_name='vrf',
        queryset=VRF.objects.all(),
        label=_('VRF (ID)'),
    )
    vrf = django_filters.ModelMultipleChoiceFilter(
        field_name='vrf__name',
        queryset=VRF.objects.all(),
        to_field_name='name',
        label=_('VRF (name)'),
    )
    prefix_id = django_filters.ModelMultipleChoiceFilter(
        field_name='prefix',
        queryset=Prefix.objects.all(),
        label=_('Prefix (ID)'),
    )
    nexthop_id = django_filters.ModelMultipleChoiceFilter(
        field_name='nexthop',
        queryset=IPAddress.objects.all(),
        label=_('Next hop (ID)'),
    )

    class Meta:
        model = StaticRoute
        fields = ('id', 'default_route', 'description')

    def search(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset

        query = (
            Q(device__name__icontains=value)
            | Q(vrf__name__icontains=value)
            | Q(description__icontains=value)
            | Q(comments__icontains=value)
        )
        if IP_LIKE.match(value):
            query |= Q(prefix__prefix__istartswith=value) | Q(nexthop__address__istartswith=value)

        return queryset.filter(query)
