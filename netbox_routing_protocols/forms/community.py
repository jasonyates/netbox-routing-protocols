from django import forms
from django.utils.translation import gettext_lazy as _

from dcim.models import Device
from netbox.forms import (
    NetBoxModelBulkEditForm,
    NetBoxModelForm,
    NetBoxModelImportForm,
    PrimaryModelFilterSetForm,
)
from utilities.forms.fields import (
    CommentField,
    CSVChoiceField,
    CSVModelChoiceField,
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    TagFilterField,
)
from utilities.forms.rendering import FieldSet

from netbox_routing_protocols.choices import ActionChoices, BGPCommunityTypeChoices
from netbox_routing_protocols.models import BGPCommunity, BGPCommunityList, BGPCommunityListRule

__all__ = (
    'BGPCommunityBulkEditForm',
    'BGPCommunityFilterForm',
    'BGPCommunityForm',
    'BGPCommunityImportForm',
    'BGPCommunityListBulkEditForm',
    'BGPCommunityListFilterForm',
    'BGPCommunityListForm',
    'BGPCommunityListImportForm',
    'BGPCommunityListRuleBulkEditForm',
    'BGPCommunityListRuleFilterForm',
    'BGPCommunityListRuleForm',
    'BGPCommunityListRuleImportForm',
)


#
# Communities
#


class BGPCommunityForm(NetBoxModelForm):
    comments = CommentField()

    fieldsets = (
        FieldSet('value', 'type', 'name', name=_('BGP Community')),
        FieldSet('description', 'tags', name=_('Attributes')),
    )

    class Meta:
        model = BGPCommunity
        fields = ('value', 'type', 'name', 'description', 'comments', 'tags')


class BGPCommunityFilterForm(PrimaryModelFilterSetForm):
    model = BGPCommunity

    type = forms.MultipleChoiceField(
        label=_('Type'),
        choices=BGPCommunityTypeChoices,
        required=False,
    )
    tag = TagFilterField(model)

    fieldsets = (
        FieldSet('q', 'filter_id', 'tag'),
        FieldSet('type', name=_('BGP Community')),
        FieldSet('owner_group_id', 'owner_id', name=_('Ownership')),
    )


class BGPCommunityBulkEditForm(NetBoxModelBulkEditForm):
    model = BGPCommunity

    type = forms.ChoiceField(
        label=_('Type'),
        choices=BGPCommunityTypeChoices,
        required=False,
    )
    description = forms.CharField(
        label=_('Description'),
        max_length=200,
        required=False,
    )
    comments = CommentField()

    fieldsets = (FieldSet('type', 'description'),)
    nullable_fields = ('description', 'comments')


class BGPCommunityImportForm(NetBoxModelImportForm):
    type = CSVChoiceField(
        label=_('Type'),
        choices=BGPCommunityTypeChoices,
        help_text=_('Community format (standard, extended or large)'),
    )

    fieldsets = (
        FieldSet('id', 'value', 'type', 'name', name=_('BGP Community')),
        FieldSet('description', 'comments', 'tags', name=_('Attributes')),
    )

    class Meta:
        model = BGPCommunity
        fields = ('value', 'type', 'name', 'description', 'comments', 'tags')


#
# Community lists
#


class BGPCommunityListForm(NetBoxModelForm):
    device = DynamicModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        required=False,
        selector=True,
        help_text=_('Leave blank to share the community list fleet-wide.'),
    )
    comments = CommentField()

    fieldsets = (
        FieldSet('device', 'name', name=_('Community List')),
        FieldSet('description', 'tags', name=_('Attributes')),
    )

    class Meta:
        model = BGPCommunityList
        fields = ('device', 'name', 'description', 'comments', 'tags')


class BGPCommunityListFilterForm(PrimaryModelFilterSetForm):
    model = BGPCommunityList

    device_id = DynamicModelMultipleChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        required=False,
    )
    tag = TagFilterField(model)

    fieldsets = (
        FieldSet('q', 'filter_id', 'tag'),
        FieldSet('device_id', name=_('Community List')),
        FieldSet('owner_group_id', 'owner_id', name=_('Ownership')),
    )


class BGPCommunityListBulkEditForm(NetBoxModelBulkEditForm):
    model = BGPCommunityList

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
    nullable_fields = ('device', 'description', 'comments')


class BGPCommunityListImportForm(NetBoxModelImportForm):
    device = CSVModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        to_field_name='name',
        required=False,
        help_text=_('Name of the device on which the community list is configured (blank for a shared list)'),
    )

    fieldsets = (
        FieldSet('id', 'device', 'name', name=_('Community List')),
        FieldSet('description', 'comments', 'tags', name=_('Attributes')),
    )

    class Meta:
        model = BGPCommunityList
        fields = ('device', 'name', 'description', 'comments', 'tags')


#
# Community list rules
#


class BGPCommunityListRuleForm(NetBoxModelForm):
    device = DynamicModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        required=False,
        selector=True,
        help_text=_('Used only to narrow the community list selection.'),
    )
    community_list = DynamicModelChoiceField(
        label=_('Community List'),
        queryset=BGPCommunityList.objects.all(),
        query_params={
            'available_on_device': '$device',
        },
    )
    community = DynamicModelChoiceField(
        label=_('Community'),
        queryset=BGPCommunity.objects.all(),
        selector=True,
    )
    comments = CommentField()

    fieldsets = (
        FieldSet('device', 'community_list', 'sequence', 'action', name=_('Community List Rule')),
        FieldSet('community', name=_('Match')),
        FieldSet('description', 'tags', name=_('Attributes')),
    )

    class Meta:
        model = BGPCommunityListRule
        fields = (
            'community_list',
            'sequence',
            'action',
            'community',
            'description',
            'comments',
            'tags',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # `device` is a convenience selector, not a model field, so seed it from the parent.
        if self.instance.pk:
            self.fields['device'].initial = self.instance.community_list.device_id


class BGPCommunityListRuleFilterForm(PrimaryModelFilterSetForm):
    model = BGPCommunityListRule

    device_id = DynamicModelMultipleChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        required=False,
    )
    community_list_id = DynamicModelMultipleChoiceField(
        label=_('Community List'),
        queryset=BGPCommunityList.objects.all(),
        required=False,
        query_params={
            'device_id': '$device_id',
        },
    )
    community_id = DynamicModelMultipleChoiceField(
        label=_('Community'),
        queryset=BGPCommunity.objects.all(),
        required=False,
    )
    action = forms.MultipleChoiceField(
        label=_('Action'),
        choices=ActionChoices,
        required=False,
    )
    tag = TagFilterField(model)

    fieldsets = (
        FieldSet('q', 'filter_id', 'tag'),
        FieldSet('device_id', 'community_list_id', 'action', name=_('Community List Rule')),
        FieldSet('community_id', name=_('Match')),
        FieldSet('owner_group_id', 'owner_id', name=_('Ownership')),
    )


class BGPCommunityListRuleBulkEditForm(NetBoxModelBulkEditForm):
    model = BGPCommunityListRule

    community_list = DynamicModelChoiceField(
        label=_('Community List'),
        queryset=BGPCommunityList.objects.all(),
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

    fieldsets = (FieldSet('community_list', 'action', 'description'),)
    nullable_fields = ('description', 'comments')


class BGPCommunityListRuleImportForm(NetBoxModelImportForm):
    device = CSVModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        to_field_name='name',
        required=False,
        help_text=_('Name of the device owning the community list (blank when the list is shared)'),
    )
    community_list = CSVModelChoiceField(
        label=_('Community List'),
        queryset=BGPCommunityList.objects.all(),
        to_field_name='name',
        help_text=_('Name of the parent community list'),
    )
    action = CSVChoiceField(
        label=_('Action'),
        choices=ActionChoices,
        help_text=_('Permit or deny'),
    )
    community = CSVModelChoiceField(
        label=_('Community'),
        queryset=BGPCommunity.objects.all(),
        to_field_name='value',
        help_text=_('Matched community value'),
    )

    fieldsets = (
        FieldSet('id', 'device', 'community_list', 'sequence', 'action', name=_('Community List Rule')),
        FieldSet('community', name=_('Match')),
        FieldSet('description', 'comments', 'tags', name=_('Attributes')),
    )

    class Meta:
        model = BGPCommunityListRule
        fields = (
            'device',
            'community_list',
            'sequence',
            'action',
            'community',
            'description',
            'comments',
            'tags',
        )

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        # Community list names are only unique per device (or among shared lists):
        # a named device selects that device's lists, a blank device selects shared ones.
        if data:
            if device := data.get('device'):
                self.fields['community_list'].queryset = BGPCommunityList.objects.filter(device__name=device)
            else:
                self.fields['community_list'].queryset = BGPCommunityList.objects.filter(device__isnull=True)
