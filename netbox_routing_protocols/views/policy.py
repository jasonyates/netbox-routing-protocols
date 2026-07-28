from django.utils.translation import gettext_lazy as _

from extras.ui.panels import CustomFieldsPanel, TagsPanel
from netbox.object_actions import AddObject, BulkDelete, BulkEdit, BulkExport, BulkImport
from netbox.ui import attrs, layout, panels
from netbox.views import generic
from utilities.query import count_related
from utilities.views import ViewTab, register_model_view

from netbox_routing_protocols import filtersets, forms, tables
from netbox_routing_protocols.models import PrefixList, PrefixListRule, RouteMap, RouteMapRule
from netbox_routing_protocols.views.base import add_child_object

__all__ = (
    'PrefixListBulkDeleteView',
    'PrefixListBulkEditView',
    'PrefixListBulkImportView',
    'PrefixListDeleteView',
    'PrefixListEditView',
    'PrefixListListView',
    'PrefixListRuleBulkDeleteView',
    'PrefixListRuleBulkEditView',
    'PrefixListRuleBulkImportView',
    'PrefixListRuleDeleteView',
    'PrefixListRuleEditView',
    'PrefixListRuleListView',
    'PrefixListRuleView',
    'PrefixListRulesView',
    'PrefixListView',
    'RouteMapBulkDeleteView',
    'RouteMapBulkEditView',
    'RouteMapBulkImportView',
    'RouteMapDeleteView',
    'RouteMapEditView',
    'RouteMapListView',
    'RouteMapRuleBulkDeleteView',
    'RouteMapRuleBulkEditView',
    'RouteMapRuleBulkImportView',
    'RouteMapRuleDeleteView',
    'RouteMapRuleEditView',
    'RouteMapRuleListView',
    'RouteMapRuleView',
    'RouteMapRulesView',
    'RouteMapView',
)


#
# Panels
#


class PrefixListPanel(panels.ObjectAttributesPanel):
    name = attrs.TextAttr('name', label=_('Name'))
    device = attrs.RelatedObjectAttr('device', label=_('Device'), linkify=True)
    address_family = attrs.ChoiceAttr('address_family', label=_('Address Family'))
    description = attrs.TextAttr('description', label=_('Description'))


class PrefixListRulePanel(panels.ObjectAttributesPanel):
    prefix_list = attrs.RelatedObjectAttr('prefix_list', label=_('Prefix List'), linkify=True)
    device = attrs.RelatedObjectAttr('prefix_list.device', label=_('Device'), linkify=True)
    sequence = attrs.NumericAttr('sequence', label=_('Sequence'))
    action = attrs.ChoiceAttr('action', label=_('Action'))
    prefix = attrs.RelatedObjectAttr('prefix', label=_('Prefix'), linkify=True)
    match_default = attrs.BooleanAttr('match_default', label=_('Match Default'))
    match_any = attrs.BooleanAttr('match_any', label=_('Match Any'))
    min_prefix_length = attrs.NumericAttr('min_prefix_length', label=_('Minimum Prefix Length'))
    max_prefix_length = attrs.NumericAttr('max_prefix_length', label=_('Maximum Prefix Length'))
    description = attrs.TextAttr('description', label=_('Description'))


class RouteMapPanel(panels.ObjectAttributesPanel):
    name = attrs.TextAttr('name', label=_('Name'))
    device = attrs.RelatedObjectAttr('device', label=_('Device'), linkify=True)
    description = attrs.TextAttr('description', label=_('Description'))


class RouteMapRulePanel(panels.ObjectAttributesPanel):
    route_map = attrs.RelatedObjectAttr('route_map', label=_('Route Map'), linkify=True)
    device = attrs.RelatedObjectAttr('route_map.device', label=_('Device'), linkify=True)
    sequence = attrs.NumericAttr('sequence', label=_('Sequence'))
    action = attrs.ChoiceAttr('action', label=_('Action'))
    prefix_list = attrs.RelatedObjectAttr('prefix_list', label=_('Match Prefix List'), linkify=True)
    match_any = attrs.BooleanAttr('match_any', label=_('Match Any'))
    description = attrs.TextAttr('description', label=_('Description'))


#
# Prefix lists
#


@register_model_view(PrefixList, 'list', path='', detail=False)
class PrefixListListView(generic.ObjectListView):
    queryset = PrefixList.objects.annotate(rule_count=count_related(PrefixListRule, 'prefix_list'))
    filterset = filtersets.PrefixListFilterSet
    filterset_form = forms.PrefixListFilterForm
    table = tables.PrefixListTable
    actions = (AddObject, BulkImport, BulkExport, BulkEdit, BulkDelete)


@register_model_view(PrefixList)
class PrefixListView(generic.ObjectView):
    queryset = PrefixList.objects.all()
    template_name = 'generic/object.html'
    layout = layout.SimpleLayout(
        left_panels=[
            PrefixListPanel(),
        ],
        right_panels=[
            TagsPanel(),
            CustomFieldsPanel(),
            panels.CommentsPanel(),
        ],
    )


@register_model_view(PrefixList, 'add', detail=False)
@register_model_view(PrefixList, 'edit')
class PrefixListEditView(generic.ObjectEditView):
    queryset = PrefixList.objects.all()
    form = forms.PrefixListForm


@register_model_view(PrefixList, 'delete')
class PrefixListDeleteView(generic.ObjectDeleteView):
    queryset = PrefixList.objects.all()


@register_model_view(PrefixList, 'bulk_import', path='import', detail=False)
class PrefixListBulkImportView(generic.BulkImportView):
    queryset = PrefixList.objects.all()
    model_form = forms.PrefixListImportForm


@register_model_view(PrefixList, 'bulk_edit', path='edit', detail=False)
class PrefixListBulkEditView(generic.BulkEditView):
    queryset = PrefixList.objects.all()
    filterset = filtersets.PrefixListFilterSet
    table = tables.PrefixListTable
    form = forms.PrefixListBulkEditForm


@register_model_view(PrefixList, 'bulk_delete', path='delete', detail=False)
class PrefixListBulkDeleteView(generic.BulkDeleteView):
    queryset = PrefixList.objects.all()
    filterset = filtersets.PrefixListFilterSet
    table = tables.PrefixListTable


@register_model_view(PrefixList, 'rules', path='rules')
class PrefixListRulesView(generic.ObjectChildrenView):
    queryset = PrefixList.objects.all()
    child_model = PrefixListRule
    table = tables.PrefixListRuleTable
    filterset = filtersets.PrefixListRuleFilterSet
    filterset_form = forms.PrefixListRuleFilterForm
    actions = (
        add_child_object(PrefixListRule, 'prefix_list', label=_('Add Rule')),
        BulkEdit,
        BulkDelete,
    )
    tab = ViewTab(
        label=_('Rules'),
        badge=lambda obj: obj.rules.count(),
        permission='netbox_routing_protocols.view_prefixlistrule',
        weight=500,
    )

    def get_children(self, request, parent):
        return parent.rules.restrict(request.user, 'view').prefetch_related('prefix_list__device', 'prefix')


#
# Prefix list rules
#


@register_model_view(PrefixListRule, 'list', path='', detail=False)
class PrefixListRuleListView(generic.ObjectListView):
    queryset = PrefixListRule.objects.all()
    filterset = filtersets.PrefixListRuleFilterSet
    filterset_form = forms.PrefixListRuleFilterForm
    table = tables.PrefixListRuleTable
    actions = (AddObject, BulkImport, BulkExport, BulkEdit, BulkDelete)


@register_model_view(PrefixListRule)
class PrefixListRuleView(generic.ObjectView):
    queryset = PrefixListRule.objects.all()
    template_name = 'generic/object.html'
    layout = layout.SimpleLayout(
        left_panels=[
            PrefixListRulePanel(),
        ],
        right_panels=[
            TagsPanel(),
            CustomFieldsPanel(),
            panels.CommentsPanel(),
        ],
    )


@register_model_view(PrefixListRule, 'add', detail=False)
@register_model_view(PrefixListRule, 'edit')
class PrefixListRuleEditView(generic.ObjectEditView):
    queryset = PrefixListRule.objects.all()
    form = forms.PrefixListRuleForm


@register_model_view(PrefixListRule, 'delete')
class PrefixListRuleDeleteView(generic.ObjectDeleteView):
    queryset = PrefixListRule.objects.all()


@register_model_view(PrefixListRule, 'bulk_import', path='import', detail=False)
class PrefixListRuleBulkImportView(generic.BulkImportView):
    queryset = PrefixListRule.objects.all()
    model_form = forms.PrefixListRuleImportForm


@register_model_view(PrefixListRule, 'bulk_edit', path='edit', detail=False)
class PrefixListRuleBulkEditView(generic.BulkEditView):
    queryset = PrefixListRule.objects.all()
    filterset = filtersets.PrefixListRuleFilterSet
    table = tables.PrefixListRuleTable
    form = forms.PrefixListRuleBulkEditForm


@register_model_view(PrefixListRule, 'bulk_delete', path='delete', detail=False)
class PrefixListRuleBulkDeleteView(generic.BulkDeleteView):
    queryset = PrefixListRule.objects.all()
    filterset = filtersets.PrefixListRuleFilterSet
    table = tables.PrefixListRuleTable


#
# Route maps
#


@register_model_view(RouteMap, 'list', path='', detail=False)
class RouteMapListView(generic.ObjectListView):
    queryset = RouteMap.objects.annotate(rule_count=count_related(RouteMapRule, 'route_map'))
    filterset = filtersets.RouteMapFilterSet
    filterset_form = forms.RouteMapFilterForm
    table = tables.RouteMapTable
    actions = (AddObject, BulkImport, BulkExport, BulkEdit, BulkDelete)


@register_model_view(RouteMap)
class RouteMapView(generic.ObjectView):
    queryset = RouteMap.objects.all()
    template_name = 'generic/object.html'
    layout = layout.SimpleLayout(
        left_panels=[
            RouteMapPanel(),
        ],
        right_panels=[
            TagsPanel(),
            CustomFieldsPanel(),
            panels.CommentsPanel(),
        ],
    )


@register_model_view(RouteMap, 'add', detail=False)
@register_model_view(RouteMap, 'edit')
class RouteMapEditView(generic.ObjectEditView):
    queryset = RouteMap.objects.all()
    form = forms.RouteMapForm


@register_model_view(RouteMap, 'delete')
class RouteMapDeleteView(generic.ObjectDeleteView):
    queryset = RouteMap.objects.all()


@register_model_view(RouteMap, 'bulk_import', path='import', detail=False)
class RouteMapBulkImportView(generic.BulkImportView):
    queryset = RouteMap.objects.all()
    model_form = forms.RouteMapImportForm


@register_model_view(RouteMap, 'bulk_edit', path='edit', detail=False)
class RouteMapBulkEditView(generic.BulkEditView):
    queryset = RouteMap.objects.all()
    filterset = filtersets.RouteMapFilterSet
    table = tables.RouteMapTable
    form = forms.RouteMapBulkEditForm


@register_model_view(RouteMap, 'bulk_delete', path='delete', detail=False)
class RouteMapBulkDeleteView(generic.BulkDeleteView):
    queryset = RouteMap.objects.all()
    filterset = filtersets.RouteMapFilterSet
    table = tables.RouteMapTable


@register_model_view(RouteMap, 'rules', path='rules')
class RouteMapRulesView(generic.ObjectChildrenView):
    queryset = RouteMap.objects.all()
    child_model = RouteMapRule
    table = tables.RouteMapRuleTable
    filterset = filtersets.RouteMapRuleFilterSet
    filterset_form = forms.RouteMapRuleFilterForm
    actions = (
        add_child_object(RouteMapRule, 'route_map', label=_('Add Rule')),
        BulkEdit,
        BulkDelete,
    )
    tab = ViewTab(
        label=_('Rules'),
        badge=lambda obj: obj.rules.count(),
        permission='netbox_routing_protocols.view_routemaprule',
        weight=500,
    )

    def get_children(self, request, parent):
        return parent.rules.restrict(request.user, 'view').prefetch_related('route_map__device', 'prefix_list')


#
# Route map rules
#


@register_model_view(RouteMapRule, 'list', path='', detail=False)
class RouteMapRuleListView(generic.ObjectListView):
    queryset = RouteMapRule.objects.all()
    filterset = filtersets.RouteMapRuleFilterSet
    filterset_form = forms.RouteMapRuleFilterForm
    table = tables.RouteMapRuleTable
    actions = (AddObject, BulkImport, BulkExport, BulkEdit, BulkDelete)


@register_model_view(RouteMapRule)
class RouteMapRuleView(generic.ObjectView):
    queryset = RouteMapRule.objects.all()
    template_name = 'generic/object.html'
    layout = layout.SimpleLayout(
        left_panels=[
            RouteMapRulePanel(),
        ],
        right_panels=[
            TagsPanel(),
            CustomFieldsPanel(),
            panels.CommentsPanel(),
        ],
    )


@register_model_view(RouteMapRule, 'add', detail=False)
@register_model_view(RouteMapRule, 'edit')
class RouteMapRuleEditView(generic.ObjectEditView):
    queryset = RouteMapRule.objects.all()
    form = forms.RouteMapRuleForm


@register_model_view(RouteMapRule, 'delete')
class RouteMapRuleDeleteView(generic.ObjectDeleteView):
    queryset = RouteMapRule.objects.all()


@register_model_view(RouteMapRule, 'bulk_import', path='import', detail=False)
class RouteMapRuleBulkImportView(generic.BulkImportView):
    queryset = RouteMapRule.objects.all()
    model_form = forms.RouteMapRuleImportForm


@register_model_view(RouteMapRule, 'bulk_edit', path='edit', detail=False)
class RouteMapRuleBulkEditView(generic.BulkEditView):
    queryset = RouteMapRule.objects.all()
    filterset = filtersets.RouteMapRuleFilterSet
    table = tables.RouteMapRuleTable
    form = forms.RouteMapRuleBulkEditForm


@register_model_view(RouteMapRule, 'bulk_delete', path='delete', detail=False)
class RouteMapRuleBulkDeleteView(generic.BulkDeleteView):
    queryset = RouteMapRule.objects.all()
    filterset = filtersets.RouteMapRuleFilterSet
    table = tables.RouteMapRuleTable
