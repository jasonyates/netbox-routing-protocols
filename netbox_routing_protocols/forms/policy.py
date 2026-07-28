from django import forms
from django.utils.translation import gettext_lazy as _

from dcim.models import Device
from ipam.models import Prefix
from netbox.forms import (
    NetBoxModelBulkEditForm,
    NetBoxModelFilterSetForm,
    NetBoxModelForm,
    NetBoxModelImportForm,
)
from utilities.forms import BOOLEAN_WITH_BLANK_CHOICES
from utilities.forms.fields import (
    CommentField,
    CSVChoiceField,
    CSVModelChoiceField,
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    TagFilterField,
)
from utilities.forms.rendering import FieldSet, TabbedGroups

from netbox_routing_protocols.choices import ActionChoices, AddressFamilyChoices
from netbox_routing_protocols.models import PrefixList, PrefixListRule, RouteMap, RouteMapRule

__all__ = (
    'PrefixListBulkEditForm',
    'PrefixListFilterForm',
    'PrefixListForm',
    'PrefixListImportForm',
    'PrefixListRuleBulkEditForm',
    'PrefixListRuleFilterForm',
    'PrefixListRuleForm',
    'PrefixListRuleImportForm',
    'RouteMapBulkEditForm',
    'RouteMapFilterForm',
    'RouteMapForm',
    'RouteMapImportForm',
    'RouteMapRuleBulkEditForm',
    'RouteMapRuleFilterForm',
    'RouteMapRuleForm',
    'RouteMapRuleImportForm',
)


#
# Prefix lists
#


class PrefixListForm(NetBoxModelForm):
    device = DynamicModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        selector=True,
    )
    comments = CommentField()

    fieldsets = (
        FieldSet('device', 'name', 'address_family', name=_('Prefix List')),
        FieldSet('description', 'tags', name=_('Attributes')),
    )

    class Meta:
        model = PrefixList
        fields = ('device', 'name', 'address_family', 'description', 'comments', 'tags')


class PrefixListFilterForm(NetBoxModelFilterSetForm):
    model = PrefixList

    device_id = DynamicModelMultipleChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        required=False,
    )
    address_family = forms.MultipleChoiceField(
        label=_('Address Family'),
        choices=AddressFamilyChoices,
        required=False,
    )
    tag = TagFilterField(model)

    fieldsets = (
        FieldSet('q', 'filter_id', 'tag'),
        FieldSet('device_id', 'address_family', name=_('Prefix List')),
    )


class PrefixListBulkEditForm(NetBoxModelBulkEditForm):
    model = PrefixList

    device = DynamicModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        required=False,
    )
    address_family = forms.ChoiceField(
        label=_('Address Family'),
        choices=AddressFamilyChoices,
        required=False,
    )
    description = forms.CharField(
        label=_('Description'),
        max_length=200,
        required=False,
    )
    comments = CommentField()

    fieldsets = (FieldSet('device', 'address_family', 'description'),)
    nullable_fields = ('description', 'comments')


class PrefixListImportForm(NetBoxModelImportForm):
    device = CSVModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        to_field_name='name',
        help_text=_('Name of the device on which the prefix list is configured'),
    )
    address_family = CSVChoiceField(
        label=_('Address Family'),
        choices=AddressFamilyChoices,
        help_text=_('IP address family (4 or 6)'),
    )

    fieldsets = (
        FieldSet('id', 'device', 'name', 'address_family', name=_('Prefix List')),
        FieldSet('description', 'comments', 'tags', name=_('Attributes')),
    )

    class Meta:
        model = PrefixList
        fields = ('device', 'name', 'address_family', 'description', 'comments', 'tags')


#
# Prefix list rules
#


class PrefixListRuleForm(NetBoxModelForm):
    device = DynamicModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        required=False,
        selector=True,
        help_text=_('Used only to narrow the prefix list selection.'),
    )
    prefix_list = DynamicModelChoiceField(
        label=_('Prefix List'),
        queryset=PrefixList.objects.all(),
        query_params={
            'device_id': '$device',
        },
    )
    prefix = DynamicModelChoiceField(
        label=_('Prefix'),
        queryset=Prefix.objects.all(),
        required=False,
        selector=True,
    )
    comments = CommentField()

    fieldsets = (
        FieldSet('device', 'prefix_list', 'sequence', 'action', name=_('Prefix List Rule')),
        FieldSet(
            TabbedGroups(
                FieldSet('prefix', 'min_prefix_length', 'max_prefix_length', name=_('Prefix')),
                FieldSet('match_any', name=_('Match Any')),
                FieldSet('match_default', name=_('Match Default')),
            ),
            name=_('Match'),
        ),
        FieldSet('description', 'tags', name=_('Attributes')),
    )

    class Meta:
        model = PrefixListRule
        fields = (
            'prefix_list',
            'sequence',
            'action',
            'prefix',
            'min_prefix_length',
            'max_prefix_length',
            'match_any',
            'match_default',
            'description',
            'comments',
            'tags',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # `device` is a convenience selector, not a model field, so seed it from the parent.
        if self.instance.pk:
            self.fields['device'].initial = self.instance.prefix_list.device_id


class PrefixListRuleFilterForm(NetBoxModelFilterSetForm):
    model = PrefixListRule

    device_id = DynamicModelMultipleChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        required=False,
    )
    prefix_list_id = DynamicModelMultipleChoiceField(
        label=_('Prefix List'),
        queryset=PrefixList.objects.all(),
        required=False,
        query_params={
            'device_id': '$device_id',
        },
    )
    prefix_id = DynamicModelMultipleChoiceField(
        label=_('Prefix'),
        queryset=Prefix.objects.all(),
        required=False,
    )
    action = forms.MultipleChoiceField(
        label=_('Action'),
        choices=ActionChoices,
        required=False,
    )
    match_any = forms.NullBooleanField(
        label=_('Match Any'),
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    match_default = forms.NullBooleanField(
        label=_('Match Default'),
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    tag = TagFilterField(model)

    fieldsets = (
        FieldSet('q', 'filter_id', 'tag'),
        FieldSet('device_id', 'prefix_list_id', 'action', name=_('Prefix List Rule')),
        FieldSet('prefix_id', 'match_any', 'match_default', name=_('Match')),
    )


class PrefixListRuleBulkEditForm(NetBoxModelBulkEditForm):
    model = PrefixListRule

    prefix_list = DynamicModelChoiceField(
        label=_('Prefix List'),
        queryset=PrefixList.objects.all(),
        required=False,
    )
    action = forms.ChoiceField(
        label=_('Action'),
        choices=ActionChoices,
        required=False,
    )
    min_prefix_length = forms.IntegerField(
        label=_('Minimum Prefix Length'),
        min_value=1,
        max_value=128,
        required=False,
    )
    max_prefix_length = forms.IntegerField(
        label=_('Maximum Prefix Length'),
        min_value=1,
        max_value=128,
        required=False,
    )
    description = forms.CharField(
        label=_('Description'),
        max_length=200,
        required=False,
    )
    comments = CommentField()

    # The match type fields (prefix / match_any / match_default) are mutually exclusive under a
    # CheckConstraint and are therefore not editable in bulk.
    fieldsets = (
        FieldSet('prefix_list', 'action', name=_('Prefix List Rule')),
        FieldSet('min_prefix_length', 'max_prefix_length', 'description', name=_('Attributes')),
    )
    nullable_fields = ('min_prefix_length', 'max_prefix_length', 'description', 'comments')


class PrefixListRuleImportForm(NetBoxModelImportForm):
    device = CSVModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        to_field_name='name',
        help_text=_('Name of the device owning the prefix list (prefix list names are unique per device)'),
    )
    prefix_list = CSVModelChoiceField(
        label=_('Prefix List'),
        queryset=PrefixList.objects.all(),
        to_field_name='name',
        help_text=_('Name of the parent prefix list'),
    )
    action = CSVChoiceField(
        label=_('Action'),
        choices=ActionChoices,
        help_text=_('Permit or deny'),
    )
    prefix = CSVModelChoiceField(
        label=_('Prefix'),
        queryset=Prefix.objects.all(),
        to_field_name='prefix',
        required=False,
        help_text=_('Matched prefix (leave blank when using match_any or match_default)'),
    )

    fieldsets = (
        FieldSet('id', 'device', 'prefix_list', 'sequence', 'action', name=_('Prefix List Rule')),
        FieldSet(
            'prefix',
            'min_prefix_length',
            'max_prefix_length',
            'match_any',
            'match_default',
            name=_('Match'),
        ),
        FieldSet('description', 'comments', 'tags', name=_('Attributes')),
    )

    class Meta:
        model = PrefixListRule
        fields = (
            'device',
            'prefix_list',
            'sequence',
            'action',
            'prefix',
            'min_prefix_length',
            'max_prefix_length',
            'match_any',
            'match_default',
            'description',
            'comments',
            'tags',
        )

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        # Prefix list names are only unique per device, so narrow the selection to the named device.
        if data and (device := data.get('device')):
            self.fields['prefix_list'].queryset = PrefixList.objects.filter(device__name=device)


#
# Route maps
#


class RouteMapForm(NetBoxModelForm):
    device = DynamicModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        selector=True,
    )
    comments = CommentField()

    fieldsets = (
        FieldSet('device', 'name', name=_('Route Map')),
        FieldSet('description', 'tags', name=_('Attributes')),
    )

    class Meta:
        model = RouteMap
        fields = ('device', 'name', 'description', 'comments', 'tags')


class RouteMapFilterForm(NetBoxModelFilterSetForm):
    model = RouteMap

    device_id = DynamicModelMultipleChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        required=False,
    )
    tag = TagFilterField(model)

    fieldsets = (
        FieldSet('q', 'filter_id', 'tag'),
        FieldSet('device_id', name=_('Route Map')),
    )


class RouteMapBulkEditForm(NetBoxModelBulkEditForm):
    model = RouteMap

    device = DynamicModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        required=False,
    )
    description = forms.CharField(
        label=_('Description'),
        max_length=200,
        required=False,
    )
    comments = CommentField()

    fieldsets = (FieldSet('device', 'description'),)
    nullable_fields = ('description', 'comments')


class RouteMapImportForm(NetBoxModelImportForm):
    device = CSVModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        to_field_name='name',
        help_text=_('Name of the device on which the route map is configured'),
    )

    fieldsets = (
        FieldSet('id', 'device', 'name', name=_('Route Map')),
        FieldSet('description', 'comments', 'tags', name=_('Attributes')),
    )

    class Meta:
        model = RouteMap
        fields = ('device', 'name', 'description', 'comments', 'tags')


#
# Route map rules
#


class RouteMapRuleForm(NetBoxModelForm):
    device = DynamicModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        required=False,
        selector=True,
        help_text=_('Used only to narrow the route map and prefix list selections.'),
    )
    route_map = DynamicModelChoiceField(
        label=_('Route Map'),
        queryset=RouteMap.objects.all(),
        query_params={
            'device_id': '$device',
        },
    )
    prefix_list = DynamicModelChoiceField(
        label=_('Match Prefix List'),
        queryset=PrefixList.objects.all(),
        required=False,
        query_params={
            'device_id': '$device',
        },
        help_text=_('Must belong to the same device as the route map.'),
    )
    comments = CommentField()

    fieldsets = (
        FieldSet('device', 'route_map', 'sequence', 'action', name=_('Route Map Rule')),
        FieldSet('prefix_list', 'match_any', name=_('Match')),
        FieldSet('description', 'tags', name=_('Attributes')),
    )

    class Meta:
        model = RouteMapRule
        fields = (
            'route_map',
            'sequence',
            'action',
            'prefix_list',
            'match_any',
            'description',
            'comments',
            'tags',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # `device` is a convenience selector, not a model field, so seed it from the parent.
        if self.instance.pk:
            self.fields['device'].initial = self.instance.route_map.device_id


class RouteMapRuleFilterForm(NetBoxModelFilterSetForm):
    model = RouteMapRule

    device_id = DynamicModelMultipleChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        required=False,
    )
    route_map_id = DynamicModelMultipleChoiceField(
        label=_('Route Map'),
        queryset=RouteMap.objects.all(),
        required=False,
        query_params={
            'device_id': '$device_id',
        },
    )
    prefix_list_id = DynamicModelMultipleChoiceField(
        label=_('Match Prefix List'),
        queryset=PrefixList.objects.all(),
        required=False,
        query_params={
            'device_id': '$device_id',
        },
    )
    action = forms.MultipleChoiceField(
        label=_('Action'),
        choices=ActionChoices,
        required=False,
    )
    match_any = forms.NullBooleanField(
        label=_('Match Any'),
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    tag = TagFilterField(model)

    fieldsets = (
        FieldSet('q', 'filter_id', 'tag'),
        FieldSet('device_id', 'route_map_id', 'action', name=_('Route Map Rule')),
        FieldSet('prefix_list_id', 'match_any', name=_('Match')),
    )


class RouteMapRuleBulkEditForm(NetBoxModelBulkEditForm):
    model = RouteMapRule

    route_map = DynamicModelChoiceField(
        label=_('Route Map'),
        queryset=RouteMap.objects.all(),
        required=False,
    )
    action = forms.ChoiceField(
        label=_('Action'),
        choices=ActionChoices,
        required=False,
    )
    description = forms.CharField(
        label=_('Description'),
        max_length=200,
        required=False,
    )
    comments = CommentField()

    # `prefix_list` and `match_any` are mutually exclusive under a CheckConstraint, so neither is
    # offered here.
    fieldsets = (FieldSet('route_map', 'action', 'description'),)
    nullable_fields = ('description', 'comments')


class RouteMapRuleImportForm(NetBoxModelImportForm):
    device = CSVModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        to_field_name='name',
        help_text=_('Name of the device owning the route map (route map names are unique per device)'),
    )
    route_map = CSVModelChoiceField(
        label=_('Route Map'),
        queryset=RouteMap.objects.all(),
        to_field_name='name',
        help_text=_('Name of the parent route map'),
    )
    action = CSVChoiceField(
        label=_('Action'),
        choices=ActionChoices,
        help_text=_('Permit or deny'),
    )
    prefix_list = CSVModelChoiceField(
        label=_('Match Prefix List'),
        queryset=PrefixList.objects.all(),
        to_field_name='name',
        required=False,
        help_text=_('Name of the matched prefix list (leave blank when using match_any)'),
    )

    fieldsets = (
        FieldSet('id', 'device', 'route_map', 'sequence', 'action', name=_('Route Map Rule')),
        FieldSet('prefix_list', 'match_any', name=_('Match')),
        FieldSet('description', 'comments', 'tags', name=_('Attributes')),
    )

    class Meta:
        model = RouteMapRule
        fields = (
            'device',
            'route_map',
            'sequence',
            'action',
            'prefix_list',
            'match_any',
            'description',
            'comments',
            'tags',
        )

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        # Route map and prefix list names are only unique per device.
        if data and (device := data.get('device')):
            self.fields['route_map'].queryset = RouteMap.objects.filter(device__name=device)
            self.fields['prefix_list'].queryset = PrefixList.objects.filter(device__name=device)
