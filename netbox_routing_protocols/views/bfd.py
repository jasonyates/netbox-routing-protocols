from django.utils.translation import gettext_lazy as _

from extras.ui.panels import CustomFieldsPanel, TagsPanel
from netbox.object_actions import AddObject, BulkDelete, BulkEdit, BulkExport, BulkImport
from netbox.ui import attrs, layout, panels
from netbox.views import generic
from utilities.views import register_model_view

from netbox_routing_protocols import filtersets, forms, tables
from netbox_routing_protocols.models import BFDProfile

__all__ = (
    'BFDProfileBulkDeleteView',
    'BFDProfileBulkEditView',
    'BFDProfileBulkImportView',
    'BFDProfileDeleteView',
    'BFDProfileEditView',
    'BFDProfileListView',
    'BFDProfileView',
)


#
# Panels
#


class BFDProfilePanel(panels.ObjectAttributesPanel):
    name = attrs.TextAttr('name', label=_('Name'))
    device = attrs.RelatedObjectAttr('device', label=_('Device'), linkify=True)
    min_tx = attrs.NumericAttr('min_tx', label=_('Minimum TX Interval'))
    min_rx = attrs.NumericAttr('min_rx', label=_('Minimum RX Interval'))
    detect_multiplier = attrs.NumericAttr('detect_multiplier', label=_('Detect Multiplier'))
    echo_mode = attrs.BooleanAttr('echo_mode', label=_('Echo Mode'))
    echo_tx = attrs.NumericAttr('echo_tx', label=_('Echo TX Interval'))
    echo_rx = attrs.NumericAttr('echo_rx', label=_('Echo RX Interval'))
    passive_mode = attrs.BooleanAttr('passive_mode', label=_('Passive Mode'))
    minimum_ttl = attrs.NumericAttr('minimum_ttl', label=_('Minimum TTL'))
    description = attrs.TextAttr('description', label=_('Description'))


#
# BFD profiles
#


@register_model_view(BFDProfile, 'list', path='', detail=False)
class BFDProfileListView(generic.ObjectListView):
    queryset = BFDProfile.objects.all()
    filterset = filtersets.BFDProfileFilterSet
    filterset_form = forms.BFDProfileFilterForm
    table = tables.BFDProfileTable
    actions = (AddObject, BulkImport, BulkExport, BulkEdit, BulkDelete)


@register_model_view(BFDProfile)
class BFDProfileView(generic.ObjectView):
    queryset = BFDProfile.objects.all()
    template_name = 'generic/object.html'
    layout = layout.SimpleLayout(
        left_panels=[
            BFDProfilePanel(),
        ],
        right_panels=[
            TagsPanel(),
            CustomFieldsPanel(),
            panels.CommentsPanel(),
        ],
    )


@register_model_view(BFDProfile, 'add', detail=False)
@register_model_view(BFDProfile, 'edit')
class BFDProfileEditView(generic.ObjectEditView):
    queryset = BFDProfile.objects.all()
    form = forms.BFDProfileForm


@register_model_view(BFDProfile, 'delete')
class BFDProfileDeleteView(generic.ObjectDeleteView):
    queryset = BFDProfile.objects.all()


@register_model_view(BFDProfile, 'bulk_import', path='import', detail=False)
class BFDProfileBulkImportView(generic.BulkImportView):
    queryset = BFDProfile.objects.all()
    model_form = forms.BFDProfileImportForm


@register_model_view(BFDProfile, 'bulk_edit', path='edit', detail=False)
class BFDProfileBulkEditView(generic.BulkEditView):
    queryset = BFDProfile.objects.all()
    filterset = filtersets.BFDProfileFilterSet
    table = tables.BFDProfileTable
    form = forms.BFDProfileBulkEditForm


@register_model_view(BFDProfile, 'bulk_delete', path='delete', detail=False)
class BFDProfileBulkDeleteView(generic.BulkDeleteView):
    queryset = BFDProfile.objects.all()
    filterset = filtersets.BFDProfileFilterSet
    table = tables.BFDProfileTable
