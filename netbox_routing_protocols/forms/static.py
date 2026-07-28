from django import forms
from django.utils.translation import gettext_lazy as _

from dcim.models import Device
from ipam.models import VRF, IPAddress, Prefix
from netbox.forms import (
    NetBoxModelBulkEditForm,
    NetBoxModelForm,
    NetBoxModelImportForm,
    PrimaryModelFilterSetForm,
)
from utilities.forms import BOOLEAN_WITH_BLANK_CHOICES
from utilities.forms.fields import (
    CommentField,
    CSVModelChoiceField,
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    TagFilterField,
)
from utilities.forms.rendering import FieldSet

from netbox_routing_protocols.models import StaticRoute

__all__ = (
    'StaticRouteBulkEditForm',
    'StaticRouteFilterForm',
    'StaticRouteForm',
    'StaticRouteImportForm',
)


class StaticRouteForm(NetBoxModelForm):
    device = DynamicModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        selector=True,
    )
    vrf = DynamicModelChoiceField(
        label=_('VRF'),
        queryset=VRF.objects.all(),
        required=False,
    )
    prefix = DynamicModelChoiceField(
        label=_('Prefix'),
        queryset=Prefix.objects.all(),
        required=False,
        selector=True,
        query_params={
            'vrf_id': '$vrf',
        },
        help_text=_('Leave empty and tick Default Route to route 0.0.0.0/0 or ::/0.'),
    )
    nexthop = DynamicModelChoiceField(
        label=_('Next Hop'),
        queryset=IPAddress.objects.all(),
        selector=True,
        query_params={
            'vrf_id': '$vrf',
        },
    )
    comments = CommentField()

    fieldsets = (
        FieldSet('device', 'vrf', name=_('Static Route')),
        FieldSet('prefix', 'default_route', 'nexthop', name=_('Destination')),
        FieldSet('description', 'tags', name=_('Attributes')),
    )

    class Meta:
        model = StaticRoute
        fields = (
            'device',
            'vrf',
            'prefix',
            'default_route',
            'nexthop',
            'description',
            'comments',
            'tags',
        )


class StaticRouteFilterForm(PrimaryModelFilterSetForm):
    model = StaticRoute

    device_id = DynamicModelMultipleChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        required=False,
    )
    vrf_id = DynamicModelMultipleChoiceField(
        label=_('VRF'),
        queryset=VRF.objects.all(),
        required=False,
    )
    prefix_id = DynamicModelMultipleChoiceField(
        label=_('Prefix'),
        queryset=Prefix.objects.all(),
        required=False,
    )
    nexthop_id = DynamicModelMultipleChoiceField(
        label=_('Next Hop'),
        queryset=IPAddress.objects.all(),
        required=False,
    )
    default_route = forms.NullBooleanField(
        label=_('Default Route'),
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    tag = TagFilterField(model)

    fieldsets = (
        FieldSet('q', 'filter_id', 'tag'),
        FieldSet('device_id', 'vrf_id', name=_('Assignment')),
        FieldSet('prefix_id', 'default_route', 'nexthop_id', name=_('Destination')),
        FieldSet('owner_group_id', 'owner_id', name=_('Ownership')),
    )


class StaticRouteBulkEditForm(NetBoxModelBulkEditForm):
    model = StaticRoute

    device = DynamicModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        required=False,
    )
    vrf = DynamicModelChoiceField(
        label=_('VRF'),
        queryset=VRF.objects.all(),
        required=False,
    )
    nexthop = DynamicModelChoiceField(
        label=_('Next Hop'),
        queryset=IPAddress.objects.all(),
        required=False,
    )
    description = forms.CharField(
        label=_('Description'),
        max_length=200,
        required=False,
    )
    comments = CommentField()

    # `prefix` and `default_route` are deliberately absent: they are mutually exclusive under a
    # CheckConstraint, so setting either in bulk would push half the selection into an illegal state.
    fieldsets = (FieldSet('device', 'vrf', 'nexthop', 'description'),)
    nullable_fields = ('vrf', 'description', 'comments')


class StaticRouteImportForm(NetBoxModelImportForm):
    device = CSVModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        to_field_name='name',
        help_text=_('Name of the device on which the route is configured'),
    )
    vrf = CSVModelChoiceField(
        label=_('VRF'),
        queryset=VRF.objects.all(),
        to_field_name='name',
        required=False,
        help_text=_('Name of the assigned VRF (leave blank for the global routing table)'),
    )
    prefix = CSVModelChoiceField(
        label=_('Prefix'),
        queryset=Prefix.objects.all(),
        to_field_name='prefix',
        required=False,
        help_text=_('Destination prefix (leave blank and set default_route instead)'),
    )
    nexthop = CSVModelChoiceField(
        label=_('Next Hop'),
        queryset=IPAddress.objects.all(),
        to_field_name='address',
        help_text=_('Next hop IP address, with mask (e.g. 192.0.2.1/32)'),
    )

    fieldsets = (
        FieldSet('id', 'device', 'vrf', name=_('Static Route')),
        FieldSet('prefix', 'default_route', 'nexthop', name=_('Destination')),
        FieldSet('description', 'comments', 'tags', name=_('Attributes')),
    )

    class Meta:
        model = StaticRoute
        fields = (
            'device',
            'vrf',
            'prefix',
            'default_route',
            'nexthop',
            'description',
            'comments',
            'tags',
        )
