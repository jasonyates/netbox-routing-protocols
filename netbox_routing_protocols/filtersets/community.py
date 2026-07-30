import django_filters
from django.db.models import Q
from django.utils.translation import gettext as _

from dcim.models import Device
from netbox.filtersets import PrimaryModelFilterSet
from utilities.filtersets import register_filterset

from netbox_routing_protocols.choices import ActionChoices, BGPCommunityTypeChoices
from netbox_routing_protocols.models import BGPCommunity, BGPCommunityList, BGPCommunityListRule

__all__ = (
    'BGPCommunityFilterSet',
    'BGPCommunityListFilterSet',
    'BGPCommunityListRuleFilterSet',
)


@register_filterset
class BGPCommunityFilterSet(PrimaryModelFilterSet):
    type = django_filters.MultipleChoiceFilter(
        choices=BGPCommunityTypeChoices,
        label=_('Type'),
    )

    class Meta:
        model = BGPCommunity
        fields = ('id', 'value', 'name', 'description')

    def search(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset

        return queryset.filter(
            Q(value__icontains=value)
            | Q(name__icontains=value)
            | Q(description__icontains=value)
            | Q(comments__icontains=value)
        )


@register_filterset
class BGPCommunityListFilterSet(PrimaryModelFilterSet):
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
    available_on_device = django_filters.ModelMultipleChoiceFilter(
        queryset=Device.objects.all(),
        method='_available_on_device',
        label=_('Available on device (ID)'),
    )
    shared = django_filters.BooleanFilter(
        field_name='device',
        lookup_expr='isnull',
        label=_('Shared (no device)'),
    )

    class Meta:
        model = BGPCommunityList
        fields = ('id', 'name', 'description')

    def _available_on_device(self, queryset, name, value):
        """Objects usable on a device: scoped to it, or shared fleet-wide."""
        if not value:
            return queryset
        return queryset.filter(Q(device__isnull=True) | Q(device__in=value))

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
class BGPCommunityListRuleFilterSet(PrimaryModelFilterSet):
    community_list_id = django_filters.ModelMultipleChoiceFilter(
        field_name='community_list',
        queryset=BGPCommunityList.objects.all(),
        label=_('Community list (ID)'),
    )
    community_list = django_filters.ModelMultipleChoiceFilter(
        field_name='community_list__name',
        queryset=BGPCommunityList.objects.all(),
        to_field_name='name',
        label=_('Community list (name)'),
    )
    device_id = django_filters.ModelMultipleChoiceFilter(
        field_name='community_list__device',
        queryset=Device.objects.all(),
        label=_('Device (ID)'),
    )
    community_id = django_filters.ModelMultipleChoiceFilter(
        field_name='community',
        queryset=BGPCommunity.objects.all(),
        label=_('Community (ID)'),
    )
    community = django_filters.ModelMultipleChoiceFilter(
        field_name='community__value',
        queryset=BGPCommunity.objects.all(),
        to_field_name='value',
        label=_('Community (value)'),
    )
    action = django_filters.MultipleChoiceFilter(
        choices=ActionChoices,
        label=_('Action'),
    )

    class Meta:
        model = BGPCommunityListRule
        fields = ('id', 'sequence', 'description')

    def search(self, queryset, name, value):
        value = value.strip()
        if not value:
            return queryset

        return queryset.filter(
            Q(community_list__name__icontains=value)
            | Q(community__value__icontains=value)
            | Q(community__name__icontains=value)
            | Q(description__icontains=value)
            | Q(comments__icontains=value)
        )
