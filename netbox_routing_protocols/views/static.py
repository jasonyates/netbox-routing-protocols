from django.utils.translation import gettext_lazy as _

from extras.ui.panels import CustomFieldsPanel, TagsPanel
from ipam.models import Prefix
from netbox.object_actions import AddObject, BulkDelete, BulkEdit, BulkExport, BulkImport
from netbox.ui import attrs, layout, panels
from netbox.views import generic
from utilities.views import ViewTab, register_model_view

from netbox_routing_protocols import filtersets, forms, tables
from netbox_routing_protocols.models import StaticRoute
from netbox_routing_protocols.views.base import add_child_object

__all__ = (
    'PrefixStaticRoutesView',
    'StaticRouteBulkDeleteView',
    'StaticRouteBulkEditView',
    'StaticRouteBulkImportView',
    'StaticRouteDeleteView',
    'StaticRouteEditView',
    'StaticRouteListView',
    'StaticRouteView',
)


#
# Panels
#


class StaticRoutePanel(panels.ObjectAttributesPanel):
    device = attrs.RelatedObjectAttr('device', label=_('Device'), linkify=True)
    vrf = attrs.RelatedObjectAttr('vrf', label=_('VRF'), linkify=True)
    prefix = attrs.RelatedObjectAttr('prefix', label=_('Prefix'), linkify=True)
    default_route = attrs.BooleanAttr('default_route', label=_('Default Route'))
    nexthop = attrs.RelatedObjectAttr('nexthop', label=_('Next Hop'), linkify=True)
    description = attrs.TextAttr('description', label=_('Description'))


#
# Static routes
#


@register_model_view(StaticRoute, 'list', path='', detail=False)
class StaticRouteListView(generic.ObjectListView):
    queryset = StaticRoute.objects.all()
    filterset = filtersets.StaticRouteFilterSet
    filterset_form = forms.StaticRouteFilterForm
    table = tables.StaticRouteTable
    actions = (AddObject, BulkImport, BulkExport, BulkEdit, BulkDelete)


@register_model_view(StaticRoute)
class StaticRouteView(generic.ObjectView):
    queryset = StaticRoute.objects.all()
    template_name = 'generic/object.html'
    layout = layout.SimpleLayout(
        left_panels=[
            StaticRoutePanel(),
        ],
        right_panels=[
            TagsPanel(),
            CustomFieldsPanel(),
            panels.CommentsPanel(),
        ],
    )


@register_model_view(StaticRoute, 'add', detail=False)
@register_model_view(StaticRoute, 'edit')
class StaticRouteEditView(generic.ObjectEditView):
    queryset = StaticRoute.objects.all()
    form = forms.StaticRouteForm


@register_model_view(StaticRoute, 'delete')
class StaticRouteDeleteView(generic.ObjectDeleteView):
    queryset = StaticRoute.objects.all()


@register_model_view(StaticRoute, 'bulk_import', path='import', detail=False)
class StaticRouteBulkImportView(generic.BulkImportView):
    queryset = StaticRoute.objects.all()
    model_form = forms.StaticRouteImportForm


@register_model_view(StaticRoute, 'bulk_edit', path='edit', detail=False)
class StaticRouteBulkEditView(generic.BulkEditView):
    queryset = StaticRoute.objects.all()
    filterset = filtersets.StaticRouteFilterSet
    table = tables.StaticRouteTable
    form = forms.StaticRouteBulkEditForm


@register_model_view(StaticRoute, 'bulk_delete', path='delete', detail=False)
class StaticRouteBulkDeleteView(generic.BulkDeleteView):
    queryset = StaticRoute.objects.all()
    filterset = filtersets.StaticRouteFilterSet
    table = tables.StaticRouteTable


#
# Tabs attached to core models
#


@register_model_view(Prefix, 'static-routes', path='static-routes')
class PrefixStaticRoutesView(generic.ObjectChildrenView):
    queryset = Prefix.objects.all()
    child_model = StaticRoute
    table = tables.StaticRouteTable
    filterset = filtersets.StaticRouteFilterSet
    filterset_form = forms.StaticRouteFilterForm
    actions = (
        add_child_object(StaticRoute, 'prefix', label=_('Add Static Route')),
        BulkEdit,
        BulkDelete,
    )
    tab = ViewTab(
        label=_('Static Routes'),
        badge=lambda obj: obj.netbox_routing_protocols_static_routes.count(),
        permission='netbox_routing_protocols.view_staticroute',
        # This tab hangs off a core model, so keep it out of the way on prefixes which have no static routes.
        hide_if_empty=True,
        weight=5000,
    )

    def get_children(self, request, parent):
        return parent.netbox_routing_protocols_static_routes.restrict(request.user, 'view').prefetch_related(
            'device', 'vrf', 'prefix', 'nexthop'
        )
