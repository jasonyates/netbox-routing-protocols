import django_filters
from django.db.models import Q
from django.utils.translation import gettext as _

from dcim.models import Device
from netbox.filtersets import PrimaryModelFilterSet
from utilities.filtersets import register_filterset

from netbox_routing_protocols.models import BFDProfile

__all__ = ('BFDProfileFilterSet',)


@register_filterset
class BFDProfileFilterSet(PrimaryModelFilterSet):
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
        model = BFDProfile
        fields = (
            'id',
            'name',
            'min_tx',
            'min_rx',
            'detect_multiplier',
            'echo_mode',
            'echo_tx',
            'echo_rx',
            'passive_mode',
            'minimum_ttl',
            'description',
        )

    def _available_on_device(self, queryset, name, value):
        """Profiles usable on a device: scoped to it, or shared fleet-wide."""
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
