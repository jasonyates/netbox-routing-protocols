from django import forms
from django.utils.translation import gettext_lazy as _

from dcim.models import Device
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
from utilities.forms.widgets import BulkEditNullBooleanSelect

from netbox_routing_protocols.models import BFDProfile

__all__ = (
    'BFDProfileBulkEditForm',
    'BFDProfileFilterForm',
    'BFDProfileForm',
    'BFDProfileImportForm',
)


class BFDProfileForm(NetBoxModelForm):
    device = DynamicModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        required=False,
        selector=True,
        help_text=_('Leave blank to share the profile fleet-wide.'),
    )
    comments = CommentField()

    fieldsets = (
        FieldSet('device', 'name', name=_('BFD Profile')),
        FieldSet('min_tx', 'min_rx', 'detect_multiplier', name=_('Intervals')),
        FieldSet('echo_mode', 'echo_tx', 'echo_rx', name=_('Echo')),
        FieldSet('passive_mode', 'minimum_ttl', name=_('Session')),
        FieldSet('description', 'tags', name=_('Attributes')),
    )

    class Meta:
        model = BFDProfile
        fields = (
            'device',
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
            'comments',
            'tags',
        )


class BFDProfileFilterForm(PrimaryModelFilterSetForm):
    model = BFDProfile

    device_id = DynamicModelMultipleChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        required=False,
    )
    echo_mode = forms.NullBooleanField(
        label=_('Echo Mode'),
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    passive_mode = forms.NullBooleanField(
        label=_('Passive Mode'),
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    tag = TagFilterField(model)

    fieldsets = (
        FieldSet('q', 'filter_id', 'tag'),
        FieldSet('device_id', 'echo_mode', 'passive_mode', name=_('BFD Profile')),
        FieldSet('owner_group_id', 'owner_id', name=_('Ownership')),
    )


class BFDProfileBulkEditForm(NetBoxModelBulkEditForm):
    model = BFDProfile

    device = DynamicModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        required=False,
    )
    min_tx = forms.IntegerField(
        label=_('Minimum TX Interval'),
        min_value=1,
        max_value=60000,
        required=False,
    )
    min_rx = forms.IntegerField(
        label=_('Minimum RX Interval'),
        min_value=1,
        max_value=60000,
        required=False,
    )
    detect_multiplier = forms.IntegerField(
        label=_('Detect Multiplier'),
        min_value=1,
        max_value=255,
        required=False,
    )
    echo_mode = forms.NullBooleanField(
        label=_('Echo Mode'),
        required=False,
        widget=BulkEditNullBooleanSelect(),
    )
    passive_mode = forms.NullBooleanField(
        label=_('Passive Mode'),
        required=False,
        widget=BulkEditNullBooleanSelect(),
    )
    minimum_ttl = forms.IntegerField(
        label=_('Minimum TTL'),
        min_value=1,
        max_value=254,
        required=False,
    )
    description = forms.CharField(
        label=_('Description'),
        max_length=200,
        required=False,
    )
    comments = CommentField()

    fieldsets = (
        FieldSet('device', 'min_tx', 'min_rx', 'detect_multiplier', name=_('BFD Profile')),
        FieldSet('echo_mode', 'passive_mode', 'minimum_ttl', 'description', name=_('Attributes')),
    )
    nullable_fields = (
        'device',
        'min_tx',
        'min_rx',
        'detect_multiplier',
        'minimum_ttl',
        'description',
        'comments',
    )


class BFDProfileImportForm(NetBoxModelImportForm):
    device = CSVModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        to_field_name='name',
        required=False,
        help_text=_('Name of the device on which the profile is configured (blank for a shared profile)'),
    )

    fieldsets = (
        FieldSet('id', 'device', 'name', name=_('BFD Profile')),
        FieldSet('min_tx', 'min_rx', 'detect_multiplier', name=_('Intervals')),
        FieldSet('echo_mode', 'echo_tx', 'echo_rx', name=_('Echo')),
        FieldSet('passive_mode', 'minimum_ttl', name=_('Session')),
        FieldSet('description', 'comments', 'tags', name=_('Attributes')),
    )

    class Meta:
        model = BFDProfile
        fields = (
            'device',
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
            'comments',
            'tags',
        )
