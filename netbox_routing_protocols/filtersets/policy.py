import re

import django_filters
from django.db.models import Q
from django.utils.translation import gettext as _

from dcim.models import Device
from ipam.models import Prefix
from netbox.filtersets import NetBoxModelFilterSet
from utilities.filtersets import register_filterset

from netbox_routing_protocols.choices import ActionChoices, AddressFamilyChoices
from netbox_routing_protocols.models import PrefixList, PrefixListRule, RouteMap, RouteMapRule

__all__ = (
    'PrefixListFilterSet',
    'PrefixListRuleFilterSet',
    'RouteMapFilterSet',
    'RouteMapRuleFilterSet',
)

# Free text is only matched against IPAM columns when it could plausibly be part of an address or
# prefix. `istartswith` is safe on NetBox's CIDR fields (it casts the column to TEXT); `contains`
# is *not* — there it means network containment and raises on non-CIDR input.
IP_LIKE = re.compile(r'^[0-9a-fA-F.:/]+$')


@register_filterset
class PrefixListFilterSet(NetBoxModelFilterSet):
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
    address_family = django_filters.MultipleChoiceFilter(
        choices=AddressFamilyChoices,
        label=_('Address family'),
    )

    class Meta:
        model = PrefixList
        fields = ('id', 'name', 'description')

    def search(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset

        return queryset.filter(
            Q(name__icontains=value)
            | Q(device__name__icontains=value)
            | Q(description__icontains=value)
            | Q(comments__icontains=value)
        )


@register_filterset
class PrefixListRuleFilterSet(NetBoxModelFilterSet):
    prefix_list_id = django_filters.ModelMultipleChoiceFilter(
        field_name='prefix_list',
        queryset=PrefixList.objects.all(),
        label=_('Prefix list (ID)'),
    )
    prefix_list = django_filters.ModelMultipleChoiceFilter(
        field_name='prefix_list__name',
        queryset=PrefixList.objects.all(),
        to_field_name='name',
        label=_('Prefix list (name)'),
    )
    device_id = django_filters.ModelMultipleChoiceFilter(
        field_name='prefix_list__device',
        queryset=Device.objects.all(),
        label=_('Device (ID)'),
    )
    device = django_filters.ModelMultipleChoiceFilter(
        field_name='prefix_list__device__name',
        queryset=Device.objects.all(),
        to_field_name='name',
        label=_('Device (name)'),
    )
    prefix_id = django_filters.ModelMultipleChoiceFilter(
        field_name='prefix',
        queryset=Prefix.objects.all(),
        label=_('Prefix (ID)'),
    )
    action = django_filters.MultipleChoiceFilter(
        choices=ActionChoices,
        label=_('Action'),
    )

    class Meta:
        model = PrefixListRule
        fields = (
            'id',
            'sequence',
            'match_any',
            'match_default',
            'min_prefix_length',
            'max_prefix_length',
            'description',
        )

    def search(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset

        query = (
            Q(prefix_list__name__icontains=value)
            | Q(prefix_list__device__name__icontains=value)
            | Q(description__icontains=value)
            | Q(comments__icontains=value)
        )
        if IP_LIKE.match(value):
            query |= Q(prefix__prefix__istartswith=value)

        return queryset.filter(query)


@register_filterset
class RouteMapFilterSet(NetBoxModelFilterSet):
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

    class Meta:
        model = RouteMap
        fields = ('id', 'name', 'description')

    def search(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset

        return queryset.filter(
            Q(name__icontains=value)
            | Q(device__name__icontains=value)
            | Q(description__icontains=value)
            | Q(comments__icontains=value)
        )


@register_filterset
class RouteMapRuleFilterSet(NetBoxModelFilterSet):
    route_map_id = django_filters.ModelMultipleChoiceFilter(
        field_name='route_map',
        queryset=RouteMap.objects.all(),
        label=_('Route map (ID)'),
    )
    route_map = django_filters.ModelMultipleChoiceFilter(
        field_name='route_map__name',
        queryset=RouteMap.objects.all(),
        to_field_name='name',
        label=_('Route map (name)'),
    )
    device_id = django_filters.ModelMultipleChoiceFilter(
        field_name='route_map__device',
        queryset=Device.objects.all(),
        label=_('Device (ID)'),
    )
    device = django_filters.ModelMultipleChoiceFilter(
        field_name='route_map__device__name',
        queryset=Device.objects.all(),
        to_field_name='name',
        label=_('Device (name)'),
    )
    prefix_list_id = django_filters.ModelMultipleChoiceFilter(
        field_name='prefix_list',
        queryset=PrefixList.objects.all(),
        label=_('Match prefix list (ID)'),
    )
    action = django_filters.MultipleChoiceFilter(
        choices=ActionChoices,
        label=_('Action'),
    )

    class Meta:
        model = RouteMapRule
        fields = ('id', 'sequence', 'match_any', 'description')

    def search(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset

        return queryset.filter(
            Q(route_map__name__icontains=value)
            | Q(route_map__device__name__icontains=value)
            | Q(prefix_list__name__icontains=value)
            | Q(description__icontains=value)
            | Q(comments__icontains=value)
        )
