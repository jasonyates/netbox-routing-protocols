from django.utils.translation import gettext_lazy as _

from extras.ui.panels import CustomFieldsPanel, TagsPanel
from netbox.object_actions import AddObject, BulkDelete, BulkEdit, BulkExport, BulkImport
from netbox.ui import attrs, layout, panels
from netbox.views import generic
from utilities.query import count_related
from utilities.views import ViewTab, register_model_view

from netbox_routing_protocols import filtersets, forms, tables
from netbox_routing_protocols.models import BGPCommunity, BGPCommunityList, BGPCommunityListRule
from netbox_routing_protocols.views.base import add_child_object

__all__ = (
    'BGPCommunitiesListView',
    'BGPCommunityBulkDeleteView',
    'BGPCommunityBulkEditView',
    'BGPCommunityBulkImportView',
    'BGPCommunityDeleteView',
    'BGPCommunityEditView',
    'BGPCommunityListBulkDeleteView',
    'BGPCommunityListBulkEditView',
    'BGPCommunityListBulkImportView',
    'BGPCommunityListDeleteView',
    'BGPCommunityListEditView',
    'BGPCommunityListRuleBulkDeleteView',
    'BGPCommunityListRuleBulkEditView',
    'BGPCommunityListRuleBulkImportView',
    'BGPCommunityListRuleDeleteView',
    'BGPCommunityListRuleEditView',
    'BGPCommunityListRuleListView',
    'BGPCommunityListRuleView',
    'BGPCommunityListRulesView',
    'BGPCommunityListView',
    'BGPCommunityListsListView',
    'BGPCommunityView',
)


#
# Panels
#


class BGPCommunityPanel(panels.ObjectAttributesPanel):
    value = attrs.TextAttr('value', label=_('Value'))
    type = attrs.ChoiceAttr('type', label=_('Type'))
    name = attrs.TextAttr('name', label=_('Name'))
    description = attrs.TextAttr('description', label=_('Description'))


class BGPCommunityListPanel(panels.ObjectAttributesPanel):
    name = attrs.TextAttr('name', label=_('Name'))
    device = attrs.RelatedObjectAttr('device', label=_('Device'), linkify=True)
    description = attrs.TextAttr('description', label=_('Description'))


class BGPCommunityListRulePanel(panels.ObjectAttributesPanel):
    community_list = attrs.RelatedObjectAttr('community_list', label=_('Community List'), linkify=True)
    device = attrs.RelatedObjectAttr('community_list.device', label=_('Device'), linkify=True)
    sequence = attrs.NumericAttr('sequence', label=_('Sequence'))
    action = attrs.ChoiceAttr('action', label=_('Action'))
    community = attrs.RelatedObjectAttr('community', label=_('Community'), linkify=True)
    description = attrs.TextAttr('description', label=_('Description'))


#
# Communities
#


@register_model_view(BGPCommunity, 'list', path='', detail=False)
class BGPCommunitiesListView(generic.ObjectListView):
    queryset = BGPCommunity.objects.all()
    filterset = filtersets.BGPCommunityFilterSet
    filterset_form = forms.BGPCommunityFilterForm
    table = tables.BGPCommunityTable
    actions = (AddObject, BulkImport, BulkExport, BulkEdit, BulkDelete)


@register_model_view(BGPCommunity)
class BGPCommunityView(generic.ObjectView):
    queryset = BGPCommunity.objects.all()
    template_name = 'generic/object.html'
    layout = layout.SimpleLayout(
        left_panels=[
            BGPCommunityPanel(),
        ],
        right_panels=[
            TagsPanel(),
            CustomFieldsPanel(),
            panels.CommentsPanel(),
        ],
    )


@register_model_view(BGPCommunity, 'add', detail=False)
@register_model_view(BGPCommunity, 'edit')
class BGPCommunityEditView(generic.ObjectEditView):
    queryset = BGPCommunity.objects.all()
    form = forms.BGPCommunityForm


@register_model_view(BGPCommunity, 'delete')
class BGPCommunityDeleteView(generic.ObjectDeleteView):
    queryset = BGPCommunity.objects.all()


@register_model_view(BGPCommunity, 'bulk_import', path='import', detail=False)
class BGPCommunityBulkImportView(generic.BulkImportView):
    queryset = BGPCommunity.objects.all()
    model_form = forms.BGPCommunityImportForm


@register_model_view(BGPCommunity, 'bulk_edit', path='edit', detail=False)
class BGPCommunityBulkEditView(generic.BulkEditView):
    queryset = BGPCommunity.objects.all()
    filterset = filtersets.BGPCommunityFilterSet
    table = tables.BGPCommunityTable
    form = forms.BGPCommunityBulkEditForm


@register_model_view(BGPCommunity, 'bulk_delete', path='delete', detail=False)
class BGPCommunityBulkDeleteView(generic.BulkDeleteView):
    queryset = BGPCommunity.objects.all()
    filterset = filtersets.BGPCommunityFilterSet
    table = tables.BGPCommunityTable


#
# Community lists
#


@register_model_view(BGPCommunityList, 'list', path='', detail=False)
class BGPCommunityListsListView(generic.ObjectListView):
    queryset = BGPCommunityList.objects.annotate(
        rule_count=count_related(BGPCommunityListRule, 'community_list'),
    )
    filterset = filtersets.BGPCommunityListFilterSet
    filterset_form = forms.BGPCommunityListFilterForm
    table = tables.BGPCommunityListTable
    actions = (AddObject, BulkImport, BulkExport, BulkEdit, BulkDelete)


@register_model_view(BGPCommunityList)
class BGPCommunityListView(generic.ObjectView):
    queryset = BGPCommunityList.objects.all()
    template_name = 'generic/object.html'
    layout = layout.SimpleLayout(
        left_panels=[
            BGPCommunityListPanel(),
        ],
        right_panels=[
            TagsPanel(),
            CustomFieldsPanel(),
            panels.CommentsPanel(),
        ],
    )


@register_model_view(BGPCommunityList, 'add', detail=False)
@register_model_view(BGPCommunityList, 'edit')
class BGPCommunityListEditView(generic.ObjectEditView):
    queryset = BGPCommunityList.objects.all()
    form = forms.BGPCommunityListForm


@register_model_view(BGPCommunityList, 'delete')
class BGPCommunityListDeleteView(generic.ObjectDeleteView):
    queryset = BGPCommunityList.objects.all()


@register_model_view(BGPCommunityList, 'bulk_import', path='import', detail=False)
class BGPCommunityListBulkImportView(generic.BulkImportView):
    queryset = BGPCommunityList.objects.all()
    model_form = forms.BGPCommunityListImportForm


@register_model_view(BGPCommunityList, 'bulk_edit', path='edit', detail=False)
class BGPCommunityListBulkEditView(generic.BulkEditView):
    queryset = BGPCommunityList.objects.all()
    filterset = filtersets.BGPCommunityListFilterSet
    table = tables.BGPCommunityListTable
    form = forms.BGPCommunityListBulkEditForm


@register_model_view(BGPCommunityList, 'bulk_delete', path='delete', detail=False)
class BGPCommunityListBulkDeleteView(generic.BulkDeleteView):
    queryset = BGPCommunityList.objects.all()
    filterset = filtersets.BGPCommunityListFilterSet
    table = tables.BGPCommunityListTable


@register_model_view(BGPCommunityList, 'rules', path='rules')
class BGPCommunityListRulesView(generic.ObjectChildrenView):
    queryset = BGPCommunityList.objects.all()
    child_model = BGPCommunityListRule
    table = tables.BGPCommunityListRuleTable
    filterset = filtersets.BGPCommunityListRuleFilterSet
    filterset_form = forms.BGPCommunityListRuleFilterForm
    actions = (
        add_child_object(BGPCommunityListRule, 'community_list', label=_('Add Rule')),
        BulkEdit,
        BulkDelete,
    )
    tab = ViewTab(
        label=_('Rules'),
        badge=lambda obj: obj.rules.count(),
        permission='netbox_routing_protocols.view_bgpcommunitylistrule',
        weight=500,
    )

    def get_children(self, request, parent):
        return parent.rules.restrict(request.user, 'view').prefetch_related('community_list__device', 'community')


#
# Community list rules
#


@register_model_view(BGPCommunityListRule, 'list', path='', detail=False)
class BGPCommunityListRuleListView(generic.ObjectListView):
    queryset = BGPCommunityListRule.objects.all()
    filterset = filtersets.BGPCommunityListRuleFilterSet
    filterset_form = forms.BGPCommunityListRuleFilterForm
    table = tables.BGPCommunityListRuleTable
    actions = (AddObject, BulkImport, BulkExport, BulkEdit, BulkDelete)


@register_model_view(BGPCommunityListRule)
class BGPCommunityListRuleView(generic.ObjectView):
    queryset = BGPCommunityListRule.objects.all()
    template_name = 'generic/object.html'
    layout = layout.SimpleLayout(
        left_panels=[
            BGPCommunityListRulePanel(),
        ],
        right_panels=[
            TagsPanel(),
            CustomFieldsPanel(),
            panels.CommentsPanel(),
        ],
    )


@register_model_view(BGPCommunityListRule, 'add', detail=False)
@register_model_view(BGPCommunityListRule, 'edit')
class BGPCommunityListRuleEditView(generic.ObjectEditView):
    queryset = BGPCommunityListRule.objects.all()
    form = forms.BGPCommunityListRuleForm


@register_model_view(BGPCommunityListRule, 'delete')
class BGPCommunityListRuleDeleteView(generic.ObjectDeleteView):
    queryset = BGPCommunityListRule.objects.all()


@register_model_view(BGPCommunityListRule, 'bulk_import', path='import', detail=False)
class BGPCommunityListRuleBulkImportView(generic.BulkImportView):
    queryset = BGPCommunityListRule.objects.all()
    model_form = forms.BGPCommunityListRuleImportForm


@register_model_view(BGPCommunityListRule, 'bulk_edit', path='edit', detail=False)
class BGPCommunityListRuleBulkEditView(generic.BulkEditView):
    queryset = BGPCommunityListRule.objects.all()
    filterset = filtersets.BGPCommunityListRuleFilterSet
    table = tables.BGPCommunityListRuleTable
    form = forms.BGPCommunityListRuleBulkEditForm


@register_model_view(BGPCommunityListRule, 'bulk_delete', path='delete', detail=False)
class BGPCommunityListRuleBulkDeleteView(generic.BulkDeleteView):
    queryset = BGPCommunityListRule.objects.all()
    filterset = filtersets.BGPCommunityListRuleFilterSet
    table = tables.BGPCommunityListRuleTable
