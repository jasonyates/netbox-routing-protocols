from django.utils.translation import gettext_lazy as _

from extras.ui.panels import CustomFieldsPanel, TagsPanel
from netbox.object_actions import AddObject, BulkDelete, BulkEdit, BulkExport, BulkImport
from netbox.ui import attrs, layout, panels
from netbox.views import generic
from utilities.query import count_related
from utilities.views import ViewTab, register_model_view

from netbox_routing_protocols import filtersets, forms, tables
from netbox_routing_protocols.models import (
    BGPAddressFamily,
    BGPAddressFamilyRedistribute,
    BGPPeer,
    BGPPeerAddressFamily,
    BGPPeergroup,
    BGPPeergroupAddressFamily,
    BGPRouter,
)
from netbox_routing_protocols.views.base import add_child_object

__all__ = (
    'BGPAddressFamilyBulkDeleteView',
    'BGPAddressFamilyBulkEditView',
    'BGPAddressFamilyBulkImportView',
    'BGPAddressFamilyDeleteView',
    'BGPAddressFamilyEditView',
    'BGPAddressFamilyListView',
    'BGPAddressFamilyRedistributeBulkDeleteView',
    'BGPAddressFamilyRedistributeBulkEditView',
    'BGPAddressFamilyRedistributeBulkImportView',
    'BGPAddressFamilyRedistributeDeleteView',
    'BGPAddressFamilyRedistributeEditView',
    'BGPAddressFamilyRedistributeListView',
    'BGPAddressFamilyRedistributeView',
    'BGPAddressFamilyRedistributionsView',
    'BGPAddressFamilyView',
    'BGPPeerAddressFamiliesView',
    'BGPPeerAddressFamilyBulkDeleteView',
    'BGPPeerAddressFamilyBulkEditView',
    'BGPPeerAddressFamilyBulkImportView',
    'BGPPeerAddressFamilyDeleteView',
    'BGPPeerAddressFamilyEditView',
    'BGPPeerAddressFamilyListView',
    'BGPPeerAddressFamilyView',
    'BGPPeerBulkDeleteView',
    'BGPPeerBulkEditView',
    'BGPPeerBulkImportView',
    'BGPPeerDeleteView',
    'BGPPeerEditView',
    'BGPPeerListView',
    'BGPPeerView',
    'BGPPeergroupAddressFamiliesView',
    'BGPPeergroupAddressFamilyBulkDeleteView',
    'BGPPeergroupAddressFamilyBulkEditView',
    'BGPPeergroupAddressFamilyBulkImportView',
    'BGPPeergroupAddressFamilyDeleteView',
    'BGPPeergroupAddressFamilyEditView',
    'BGPPeergroupAddressFamilyListView',
    'BGPPeergroupAddressFamilyView',
    'BGPPeergroupBulkDeleteView',
    'BGPPeergroupBulkEditView',
    'BGPPeergroupBulkImportView',
    'BGPPeergroupDeleteView',
    'BGPPeergroupEditView',
    'BGPPeergroupListView',
    'BGPPeergroupPeersView',
    'BGPPeergroupView',
    'BGPRouterAddressFamiliesView',
    'BGPRouterBulkDeleteView',
    'BGPRouterBulkEditView',
    'BGPRouterBulkImportView',
    'BGPRouterDeleteView',
    'BGPRouterEditView',
    'BGPRouterListView',
    'BGPRouterPeergroupsView',
    'BGPRouterPeersView',
    'BGPRouterView',
)


#
# Panels
#


class BGPRouterPanel(panels.ObjectAttributesPanel):
    device = attrs.RelatedObjectAttr('device', label=_('Device'), linkify=True)
    vrf = attrs.RelatedObjectAttr('vrf', label=_('VRF'), linkify=True)
    enable = attrs.BooleanAttr('enable', label=_('Enabled'))
    asn = attrs.RelatedObjectAttr('asn', label=_('ASN'), linkify=True)
    router_id = attrs.RelatedObjectAttr('router_id', label=_('Router ID'), linkify=True)
    multipath_relax = attrs.BooleanAttr('multipath_relax', label=_('Multipath Relax'))
    route_reflection = attrs.BooleanAttr('route_reflection', label=_('Route Reflection'))
    enable_evpn = attrs.BooleanAttr('enable_evpn', label=_('Enable EVPN'))
    description = attrs.TextAttr('description', label=_('Description'))


class BGPPeergroupPanel(panels.ObjectAttributesPanel):
    name = attrs.TextAttr('name', label=_('Name'))
    bgprouter = attrs.RelatedObjectAttr('bgprouter', label=_('BGP Router'), linkify=True)
    # `device` and `vrf` are properties reaching through the router.
    device = attrs.RelatedObjectAttr('device', label=_('Device'), linkify=True)
    vrf = attrs.RelatedObjectAttr('vrf', label=_('VRF'), linkify=True)
    enable = attrs.BooleanAttr('enable', label=_('Enabled'))
    remote_as = attrs.RelatedObjectAttr('remote_as', label=_('Remote AS'), linkify=True)
    bfd = attrs.RelatedObjectAttr('bfd', label=_('BFD Profile'), linkify=True)
    ebgp_multihop = attrs.BooleanAttr('ebgp_multihop', label=_('eBGP Multihop'))
    ebgp_multihop_ttl = attrs.NumericAttr('ebgp_multihop_ttl', label=_('eBGP Multihop TTL'))
    description = attrs.TextAttr('description', label=_('Description'))


class BGPPeerPanel(panels.ObjectAttributesPanel):
    bgprouter = attrs.RelatedObjectAttr('bgprouter', label=_('BGP Router'), linkify=True)
    device = attrs.RelatedObjectAttr('device', label=_('Device'), linkify=True)
    vrf = attrs.RelatedObjectAttr('vrf', label=_('VRF'), linkify=True)
    remote_address = attrs.RelatedObjectAttr('remote_address', label=_('Remote Address'), linkify=True)
    interface = attrs.RelatedObjectAttr('interface', label=_('Interface'), linkify=True)
    peergroup = attrs.RelatedObjectAttr('peergroup', label=_('Peer Group'), linkify=True)
    enable = attrs.BooleanAttr('enable', label=_('Enabled'))
    remote_as = attrs.RelatedObjectAttr('remote_as', label=_('Remote AS'), linkify=True)
    bfd = attrs.RelatedObjectAttr('bfd', label=_('BFD Profile'), linkify=True)
    ebgp_multihop = attrs.BooleanAttr('ebgp_multihop', label=_('eBGP Multihop'))
    ebgp_multihop_ttl = attrs.NumericAttr('ebgp_multihop_ttl', label=_('eBGP Multihop TTL'))
    description = attrs.TextAttr('description', label=_('Description'))


class BGPAddressFamilyPanel(panels.ObjectAttributesPanel):
    bgprouter = attrs.RelatedObjectAttr('bgprouter', label=_('BGP Router'), linkify=True)
    device = attrs.RelatedObjectAttr('device', label=_('Device'), linkify=True)
    vrf = attrs.RelatedObjectAttr('vrf', label=_('VRF'), linkify=True)
    family = attrs.ChoiceAttr('family', label=_('Address Family'))
    enable = attrs.BooleanAttr('enable', label=_('Enabled'))
    aggregate_routes = attrs.RelatedObjectListAttr('aggregate_routes', label=_('Aggregate Routes'), linkify=True)
    aggregate_route_map = attrs.RelatedObjectAttr('aggregate_route_map', label=_('Aggregate Route Map'), linkify=True)
    networks = attrs.RelatedObjectListAttr('networks', label=_('Network Statements'), linkify=True)
    network_route_map = attrs.RelatedObjectAttr('network_route_map', label=_('Network Route Map'), linkify=True)
    export_to_evpn = attrs.BooleanAttr('export_to_evpn', label=_('Export to EVPN'))
    description = attrs.TextAttr('description', label=_('Description'))


class BGPAddressFamilyRedistributePanel(panels.ObjectAttributesPanel):
    family = attrs.RelatedObjectAttr('family', label=_('Address Family'), linkify=True)
    bgprouter = attrs.RelatedObjectAttr('family.bgprouter', label=_('BGP Router'), linkify=True)
    protocol = attrs.ChoiceAttr('protocol', label=_('Protocol'))
    enable = attrs.BooleanAttr('enable', label=_('Enabled'))
    route_map = attrs.RelatedObjectAttr('route_map', label=_('Route Map'), linkify=True)
    description = attrs.TextAttr('description', label=_('Description'))


class BGPPeerAddressFamilyPanel(panels.ObjectAttributesPanel):
    peer = attrs.RelatedObjectAttr('peer', label=_('BGP Peer'), linkify=True)
    bgprouter = attrs.RelatedObjectAttr('peer.bgprouter', label=_('BGP Router'), linkify=True)
    family = attrs.ChoiceAttr('family', label=_('Address Family'))
    enable = attrs.BooleanAttr('enable', label=_('Enabled'))
    inbound_policy = attrs.RelatedObjectAttr('inbound_policy', label=_('Inbound Policy'), linkify=True)
    outbound_policy = attrs.RelatedObjectAttr('outbound_policy', label=_('Outbound Policy'), linkify=True)
    soft_reconfiguration = attrs.BooleanAttr('soft_reconfiguration', label=_('Soft Reconfiguration'))
    default_originate = attrs.BooleanAttr('default_originate', label=_('Default Originate'))
    route_reflector_client = attrs.BooleanAttr('route_reflector_client', label=_('Route Reflector Client'))
    description = attrs.TextAttr('description', label=_('Description'))


class BGPPeergroupAddressFamilyPanel(panels.ObjectAttributesPanel):
    peergroup = attrs.RelatedObjectAttr('peergroup', label=_('BGP Peer Group'), linkify=True)
    bgprouter = attrs.RelatedObjectAttr('peergroup.bgprouter', label=_('BGP Router'), linkify=True)
    family = attrs.ChoiceAttr('family', label=_('Address Family'))
    enable = attrs.BooleanAttr('enable', label=_('Enabled'))
    inbound_policy = attrs.RelatedObjectAttr('inbound_policy', label=_('Inbound Policy'), linkify=True)
    outbound_policy = attrs.RelatedObjectAttr('outbound_policy', label=_('Outbound Policy'), linkify=True)
    soft_reconfiguration = attrs.BooleanAttr('soft_reconfiguration', label=_('Soft Reconfiguration'))
    default_originate = attrs.BooleanAttr('default_originate', label=_('Default Originate'))
    route_reflector_client = attrs.BooleanAttr('route_reflector_client', label=_('Route Reflector Client'))
    description = attrs.TextAttr('description', label=_('Description'))


#
# BGP routers
#


@register_model_view(BGPRouter, 'list', path='', detail=False)
class BGPRouterListView(generic.ObjectListView):
    queryset = BGPRouter.objects.all()
    filterset = filtersets.BGPRouterFilterSet
    filterset_form = forms.BGPRouterFilterForm
    table = tables.BGPRouterTable
    actions = (AddObject, BulkImport, BulkExport, BulkEdit, BulkDelete)


@register_model_view(BGPRouter)
class BGPRouterView(generic.ObjectView):
    queryset = BGPRouter.objects.all()
    template_name = 'generic/object.html'
    layout = layout.SimpleLayout(
        left_panels=[
            BGPRouterPanel(),
        ],
        right_panels=[
            TagsPanel(),
            CustomFieldsPanel(),
            panels.CommentsPanel(),
        ],
    )


@register_model_view(BGPRouter, 'add', detail=False)
@register_model_view(BGPRouter, 'edit')
class BGPRouterEditView(generic.ObjectEditView):
    queryset = BGPRouter.objects.all()
    form = forms.BGPRouterForm


@register_model_view(BGPRouter, 'delete')
class BGPRouterDeleteView(generic.ObjectDeleteView):
    queryset = BGPRouter.objects.all()


@register_model_view(BGPRouter, 'bulk_import', path='import', detail=False)
class BGPRouterBulkImportView(generic.BulkImportView):
    queryset = BGPRouter.objects.all()
    model_form = forms.BGPRouterImportForm


@register_model_view(BGPRouter, 'bulk_edit', path='edit', detail=False)
class BGPRouterBulkEditView(generic.BulkEditView):
    queryset = BGPRouter.objects.all()
    filterset = filtersets.BGPRouterFilterSet
    table = tables.BGPRouterTable
    form = forms.BGPRouterBulkEditForm


@register_model_view(BGPRouter, 'bulk_delete', path='delete', detail=False)
class BGPRouterBulkDeleteView(generic.BulkDeleteView):
    queryset = BGPRouter.objects.all()
    filterset = filtersets.BGPRouterFilterSet
    table = tables.BGPRouterTable


@register_model_view(BGPRouter, 'address-families', path='address-families')
class BGPRouterAddressFamiliesView(generic.ObjectChildrenView):
    queryset = BGPRouter.objects.all()
    child_model = BGPAddressFamily
    table = tables.BGPAddressFamilyTable
    filterset = filtersets.BGPAddressFamilyFilterSet
    filterset_form = forms.BGPAddressFamilyFilterForm
    actions = (
        add_child_object(BGPAddressFamily, 'bgprouter', label=_('Add Address Family')),
        BulkEdit,
        BulkDelete,
    )
    tab = ViewTab(
        label=_('Address Families'),
        badge=lambda obj: obj.address_families.count(),
        permission='netbox_routing_protocols.view_bgpaddressfamily',
        weight=500,
    )

    def get_children(self, request, parent):
        return parent.address_families.restrict(request.user, 'view').prefetch_related(
            'bgprouter__device', 'bgprouter__vrf', 'aggregate_route_map', 'network_route_map'
        )


@register_model_view(BGPRouter, 'peers', path='peers')
class BGPRouterPeersView(generic.ObjectChildrenView):
    queryset = BGPRouter.objects.all()
    child_model = BGPPeer
    table = tables.BGPPeerTable
    filterset = filtersets.BGPPeerFilterSet
    filterset_form = forms.BGPPeerFilterForm
    actions = (
        add_child_object(BGPPeer, 'bgprouter', label=_('Add Peer')),
        BulkEdit,
        BulkDelete,
    )
    tab = ViewTab(
        label=_('Peers'),
        badge=lambda obj: obj.bgppeers.count(),
        permission='netbox_routing_protocols.view_bgppeer',
        weight=510,
    )

    def get_children(self, request, parent):
        return parent.bgppeers.restrict(request.user, 'view').prefetch_related(
            'bgprouter__device', 'bgprouter__vrf', 'remote_address', 'interface', 'peergroup', 'remote_as'
        )


@register_model_view(BGPRouter, 'peer-groups', path='peer-groups')
class BGPRouterPeergroupsView(generic.ObjectChildrenView):
    queryset = BGPRouter.objects.all()
    child_model = BGPPeergroup
    table = tables.BGPPeergroupTable
    filterset = filtersets.BGPPeergroupFilterSet
    filterset_form = forms.BGPPeergroupFilterForm
    actions = (
        add_child_object(BGPPeergroup, 'bgprouter', label=_('Add Peer Group')),
        BulkEdit,
        BulkDelete,
    )
    tab = ViewTab(
        label=_('Peer Groups'),
        badge=lambda obj: obj.bgppeergroups.count(),
        permission='netbox_routing_protocols.view_bgppeergroup',
        weight=520,
    )

    def get_children(self, request, parent):
        return parent.bgppeergroups.restrict(request.user, 'view').prefetch_related(
            'bgprouter__device', 'bgprouter__vrf', 'remote_as'
        )


#
# BGP peer groups
#


@register_model_view(BGPPeergroup, 'list', path='', detail=False)
class BGPPeergroupListView(generic.ObjectListView):
    queryset = BGPPeergroup.objects.annotate(peer_count=count_related(BGPPeer, 'peergroup'))
    filterset = filtersets.BGPPeergroupFilterSet
    filterset_form = forms.BGPPeergroupFilterForm
    table = tables.BGPPeergroupTable
    actions = (AddObject, BulkImport, BulkExport, BulkEdit, BulkDelete)


@register_model_view(BGPPeergroup)
class BGPPeergroupView(generic.ObjectView):
    queryset = BGPPeergroup.objects.all()
    template_name = 'generic/object.html'
    layout = layout.SimpleLayout(
        left_panels=[
            BGPPeergroupPanel(),
        ],
        right_panels=[
            TagsPanel(),
            CustomFieldsPanel(),
            panels.CommentsPanel(),
        ],
    )


@register_model_view(BGPPeergroup, 'add', detail=False)
@register_model_view(BGPPeergroup, 'edit')
class BGPPeergroupEditView(generic.ObjectEditView):
    queryset = BGPPeergroup.objects.all()
    form = forms.BGPPeergroupForm


@register_model_view(BGPPeergroup, 'delete')
class BGPPeergroupDeleteView(generic.ObjectDeleteView):
    queryset = BGPPeergroup.objects.all()


@register_model_view(BGPPeergroup, 'bulk_import', path='import', detail=False)
class BGPPeergroupBulkImportView(generic.BulkImportView):
    queryset = BGPPeergroup.objects.all()
    model_form = forms.BGPPeergroupImportForm


@register_model_view(BGPPeergroup, 'bulk_edit', path='edit', detail=False)
class BGPPeergroupBulkEditView(generic.BulkEditView):
    queryset = BGPPeergroup.objects.all()
    filterset = filtersets.BGPPeergroupFilterSet
    table = tables.BGPPeergroupTable
    form = forms.BGPPeergroupBulkEditForm


@register_model_view(BGPPeergroup, 'bulk_delete', path='delete', detail=False)
class BGPPeergroupBulkDeleteView(generic.BulkDeleteView):
    queryset = BGPPeergroup.objects.all()
    filterset = filtersets.BGPPeergroupFilterSet
    table = tables.BGPPeergroupTable


@register_model_view(BGPPeergroup, 'address-families', path='address-families')
class BGPPeergroupAddressFamiliesView(generic.ObjectChildrenView):
    queryset = BGPPeergroup.objects.all()
    child_model = BGPPeergroupAddressFamily
    table = tables.BGPPeergroupAddressFamilyTable
    filterset = filtersets.BGPPeergroupAddressFamilyFilterSet
    filterset_form = forms.BGPPeergroupAddressFamilyFilterForm
    actions = (
        add_child_object(BGPPeergroupAddressFamily, 'peergroup', label=_('Add Address Family')),
        BulkEdit,
        BulkDelete,
    )
    tab = ViewTab(
        label=_('Address Families'),
        badge=lambda obj: obj.address_families.count(),
        permission='netbox_routing_protocols.view_bgppeergroupaddressfamily',
        weight=500,
    )

    def get_children(self, request, parent):
        return parent.address_families.restrict(request.user, 'view').prefetch_related(
            'peergroup__bgprouter__device', 'peergroup__bgprouter__vrf', 'inbound_policy', 'outbound_policy'
        )


@register_model_view(BGPPeergroup, 'peers', path='peers')
class BGPPeergroupPeersView(generic.ObjectChildrenView):
    queryset = BGPPeergroup.objects.all()
    child_model = BGPPeer
    table = tables.BGPPeerTable
    filterset = filtersets.BGPPeerFilterSet
    filterset_form = forms.BGPPeerFilterForm
    actions = (
        add_child_object(
            BGPPeer,
            'peergroup',
            label=_('Add Peer'),
            # A peer belongs to the same router as its peer group, so seed that too.
            extra_params={'bgprouter': lambda obj: obj.bgprouter_id},
        ),
        BulkEdit,
        BulkDelete,
    )
    tab = ViewTab(
        label=_('Peers'),
        badge=lambda obj: obj.peers.count(),
        permission='netbox_routing_protocols.view_bgppeer',
        weight=510,
    )

    def get_children(self, request, parent):
        return parent.peers.restrict(request.user, 'view').prefetch_related(
            'bgprouter__device', 'bgprouter__vrf', 'remote_address', 'interface', 'remote_as'
        )


#
# BGP peers
#


@register_model_view(BGPPeer, 'list', path='', detail=False)
class BGPPeerListView(generic.ObjectListView):
    queryset = BGPPeer.objects.all()
    filterset = filtersets.BGPPeerFilterSet
    filterset_form = forms.BGPPeerFilterForm
    table = tables.BGPPeerTable
    actions = (AddObject, BulkImport, BulkExport, BulkEdit, BulkDelete)


@register_model_view(BGPPeer)
class BGPPeerView(generic.ObjectView):
    queryset = BGPPeer.objects.all()
    template_name = 'generic/object.html'
    layout = layout.SimpleLayout(
        left_panels=[
            BGPPeerPanel(),
        ],
        right_panels=[
            TagsPanel(),
            CustomFieldsPanel(),
            panels.CommentsPanel(),
        ],
    )


@register_model_view(BGPPeer, 'add', detail=False)
@register_model_view(BGPPeer, 'edit')
class BGPPeerEditView(generic.ObjectEditView):
    queryset = BGPPeer.objects.all()
    form = forms.BGPPeerForm


@register_model_view(BGPPeer, 'delete')
class BGPPeerDeleteView(generic.ObjectDeleteView):
    queryset = BGPPeer.objects.all()


@register_model_view(BGPPeer, 'bulk_import', path='import', detail=False)
class BGPPeerBulkImportView(generic.BulkImportView):
    queryset = BGPPeer.objects.all()
    model_form = forms.BGPPeerImportForm


@register_model_view(BGPPeer, 'bulk_edit', path='edit', detail=False)
class BGPPeerBulkEditView(generic.BulkEditView):
    queryset = BGPPeer.objects.all()
    filterset = filtersets.BGPPeerFilterSet
    table = tables.BGPPeerTable
    form = forms.BGPPeerBulkEditForm


@register_model_view(BGPPeer, 'bulk_delete', path='delete', detail=False)
class BGPPeerBulkDeleteView(generic.BulkDeleteView):
    queryset = BGPPeer.objects.all()
    filterset = filtersets.BGPPeerFilterSet
    table = tables.BGPPeerTable


@register_model_view(BGPPeer, 'address-families', path='address-families')
class BGPPeerAddressFamiliesView(generic.ObjectChildrenView):
    queryset = BGPPeer.objects.all()
    child_model = BGPPeerAddressFamily
    table = tables.BGPPeerAddressFamilyTable
    filterset = filtersets.BGPPeerAddressFamilyFilterSet
    filterset_form = forms.BGPPeerAddressFamilyFilterForm
    actions = (
        add_child_object(BGPPeerAddressFamily, 'peer', label=_('Add Address Family')),
        BulkEdit,
        BulkDelete,
    )
    tab = ViewTab(
        label=_('Address Families'),
        badge=lambda obj: obj.address_families.count(),
        permission='netbox_routing_protocols.view_bgppeeraddressfamily',
        weight=500,
    )

    def get_children(self, request, parent):
        return parent.address_families.restrict(request.user, 'view').prefetch_related(
            'peer__bgprouter__device', 'peer__bgprouter__vrf', 'inbound_policy', 'outbound_policy'
        )


#
# BGP address families
#


@register_model_view(BGPAddressFamily, 'list', path='', detail=False)
class BGPAddressFamilyListView(generic.ObjectListView):
    queryset = BGPAddressFamily.objects.all()
    filterset = filtersets.BGPAddressFamilyFilterSet
    filterset_form = forms.BGPAddressFamilyFilterForm
    table = tables.BGPAddressFamilyTable
    actions = (AddObject, BulkImport, BulkExport, BulkEdit, BulkDelete)


@register_model_view(BGPAddressFamily)
class BGPAddressFamilyView(generic.ObjectView):
    queryset = BGPAddressFamily.objects.all()
    template_name = 'generic/object.html'
    layout = layout.SimpleLayout(
        left_panels=[
            BGPAddressFamilyPanel(),
        ],
        right_panels=[
            TagsPanel(),
            CustomFieldsPanel(),
            panels.CommentsPanel(),
        ],
    )


@register_model_view(BGPAddressFamily, 'add', detail=False)
@register_model_view(BGPAddressFamily, 'edit')
class BGPAddressFamilyEditView(generic.ObjectEditView):
    queryset = BGPAddressFamily.objects.all()
    form = forms.BGPAddressFamilyForm


@register_model_view(BGPAddressFamily, 'delete')
class BGPAddressFamilyDeleteView(generic.ObjectDeleteView):
    queryset = BGPAddressFamily.objects.all()


@register_model_view(BGPAddressFamily, 'bulk_import', path='import', detail=False)
class BGPAddressFamilyBulkImportView(generic.BulkImportView):
    queryset = BGPAddressFamily.objects.all()
    model_form = forms.BGPAddressFamilyImportForm


@register_model_view(BGPAddressFamily, 'bulk_edit', path='edit', detail=False)
class BGPAddressFamilyBulkEditView(generic.BulkEditView):
    queryset = BGPAddressFamily.objects.all()
    filterset = filtersets.BGPAddressFamilyFilterSet
    table = tables.BGPAddressFamilyTable
    form = forms.BGPAddressFamilyBulkEditForm


@register_model_view(BGPAddressFamily, 'bulk_delete', path='delete', detail=False)
class BGPAddressFamilyBulkDeleteView(generic.BulkDeleteView):
    queryset = BGPAddressFamily.objects.all()
    filterset = filtersets.BGPAddressFamilyFilterSet
    table = tables.BGPAddressFamilyTable


@register_model_view(BGPAddressFamily, 'redistributions', path='redistributions')
class BGPAddressFamilyRedistributionsView(generic.ObjectChildrenView):
    queryset = BGPAddressFamily.objects.all()
    child_model = BGPAddressFamilyRedistribute
    table = tables.BGPAddressFamilyRedistributeTable
    filterset = filtersets.BGPAddressFamilyRedistributeFilterSet
    filterset_form = forms.BGPAddressFamilyRedistributeFilterForm
    actions = (
        add_child_object(BGPAddressFamilyRedistribute, 'family', label=_('Add Redistribution')),
        BulkEdit,
        BulkDelete,
    )
    tab = ViewTab(
        label=_('Redistributions'),
        badge=lambda obj: obj.redistributions.count(),
        permission='netbox_routing_protocols.view_bgpaddressfamilyredistribute',
        weight=500,
    )

    def get_children(self, request, parent):
        return parent.redistributions.restrict(request.user, 'view').prefetch_related(
            'family__bgprouter__device', 'family__bgprouter__vrf', 'route_map'
        )


#
# BGP redistributions
#


@register_model_view(BGPAddressFamilyRedistribute, 'list', path='', detail=False)
class BGPAddressFamilyRedistributeListView(generic.ObjectListView):
    queryset = BGPAddressFamilyRedistribute.objects.all()
    filterset = filtersets.BGPAddressFamilyRedistributeFilterSet
    filterset_form = forms.BGPAddressFamilyRedistributeFilterForm
    table = tables.BGPAddressFamilyRedistributeTable
    actions = (AddObject, BulkImport, BulkExport, BulkEdit, BulkDelete)


@register_model_view(BGPAddressFamilyRedistribute)
class BGPAddressFamilyRedistributeView(generic.ObjectView):
    queryset = BGPAddressFamilyRedistribute.objects.all()
    template_name = 'generic/object.html'
    layout = layout.SimpleLayout(
        left_panels=[
            BGPAddressFamilyRedistributePanel(),
        ],
        right_panels=[
            TagsPanel(),
            CustomFieldsPanel(),
            panels.CommentsPanel(),
        ],
    )


@register_model_view(BGPAddressFamilyRedistribute, 'add', detail=False)
@register_model_view(BGPAddressFamilyRedistribute, 'edit')
class BGPAddressFamilyRedistributeEditView(generic.ObjectEditView):
    queryset = BGPAddressFamilyRedistribute.objects.all()
    form = forms.BGPAddressFamilyRedistributeForm


@register_model_view(BGPAddressFamilyRedistribute, 'delete')
class BGPAddressFamilyRedistributeDeleteView(generic.ObjectDeleteView):
    queryset = BGPAddressFamilyRedistribute.objects.all()


@register_model_view(BGPAddressFamilyRedistribute, 'bulk_import', path='import', detail=False)
class BGPAddressFamilyRedistributeBulkImportView(generic.BulkImportView):
    queryset = BGPAddressFamilyRedistribute.objects.all()
    model_form = forms.BGPAddressFamilyRedistributeImportForm


@register_model_view(BGPAddressFamilyRedistribute, 'bulk_edit', path='edit', detail=False)
class BGPAddressFamilyRedistributeBulkEditView(generic.BulkEditView):
    queryset = BGPAddressFamilyRedistribute.objects.all()
    filterset = filtersets.BGPAddressFamilyRedistributeFilterSet
    table = tables.BGPAddressFamilyRedistributeTable
    form = forms.BGPAddressFamilyRedistributeBulkEditForm


@register_model_view(BGPAddressFamilyRedistribute, 'bulk_delete', path='delete', detail=False)
class BGPAddressFamilyRedistributeBulkDeleteView(generic.BulkDeleteView):
    queryset = BGPAddressFamilyRedistribute.objects.all()
    filterset = filtersets.BGPAddressFamilyRedistributeFilterSet
    table = tables.BGPAddressFamilyRedistributeTable


#
# BGP peer address families
#


@register_model_view(BGPPeerAddressFamily, 'list', path='', detail=False)
class BGPPeerAddressFamilyListView(generic.ObjectListView):
    queryset = BGPPeerAddressFamily.objects.all()
    filterset = filtersets.BGPPeerAddressFamilyFilterSet
    filterset_form = forms.BGPPeerAddressFamilyFilterForm
    table = tables.BGPPeerAddressFamilyTable
    actions = (AddObject, BulkImport, BulkExport, BulkEdit, BulkDelete)


@register_model_view(BGPPeerAddressFamily)
class BGPPeerAddressFamilyView(generic.ObjectView):
    queryset = BGPPeerAddressFamily.objects.all()
    template_name = 'generic/object.html'
    layout = layout.SimpleLayout(
        left_panels=[
            BGPPeerAddressFamilyPanel(),
        ],
        right_panels=[
            TagsPanel(),
            CustomFieldsPanel(),
            panels.CommentsPanel(),
        ],
    )


@register_model_view(BGPPeerAddressFamily, 'add', detail=False)
@register_model_view(BGPPeerAddressFamily, 'edit')
class BGPPeerAddressFamilyEditView(generic.ObjectEditView):
    queryset = BGPPeerAddressFamily.objects.all()
    form = forms.BGPPeerAddressFamilyForm


@register_model_view(BGPPeerAddressFamily, 'delete')
class BGPPeerAddressFamilyDeleteView(generic.ObjectDeleteView):
    queryset = BGPPeerAddressFamily.objects.all()


@register_model_view(BGPPeerAddressFamily, 'bulk_import', path='import', detail=False)
class BGPPeerAddressFamilyBulkImportView(generic.BulkImportView):
    queryset = BGPPeerAddressFamily.objects.all()
    model_form = forms.BGPPeerAddressFamilyImportForm


@register_model_view(BGPPeerAddressFamily, 'bulk_edit', path='edit', detail=False)
class BGPPeerAddressFamilyBulkEditView(generic.BulkEditView):
    queryset = BGPPeerAddressFamily.objects.all()
    filterset = filtersets.BGPPeerAddressFamilyFilterSet
    table = tables.BGPPeerAddressFamilyTable
    form = forms.BGPPeerAddressFamilyBulkEditForm


@register_model_view(BGPPeerAddressFamily, 'bulk_delete', path='delete', detail=False)
class BGPPeerAddressFamilyBulkDeleteView(generic.BulkDeleteView):
    queryset = BGPPeerAddressFamily.objects.all()
    filterset = filtersets.BGPPeerAddressFamilyFilterSet
    table = tables.BGPPeerAddressFamilyTable


#
# BGP peer group address families
#


@register_model_view(BGPPeergroupAddressFamily, 'list', path='', detail=False)
class BGPPeergroupAddressFamilyListView(generic.ObjectListView):
    queryset = BGPPeergroupAddressFamily.objects.all()
    filterset = filtersets.BGPPeergroupAddressFamilyFilterSet
    filterset_form = forms.BGPPeergroupAddressFamilyFilterForm
    table = tables.BGPPeergroupAddressFamilyTable
    actions = (AddObject, BulkImport, BulkExport, BulkEdit, BulkDelete)


@register_model_view(BGPPeergroupAddressFamily)
class BGPPeergroupAddressFamilyView(generic.ObjectView):
    queryset = BGPPeergroupAddressFamily.objects.all()
    template_name = 'generic/object.html'
    layout = layout.SimpleLayout(
        left_panels=[
            BGPPeergroupAddressFamilyPanel(),
        ],
        right_panels=[
            TagsPanel(),
            CustomFieldsPanel(),
            panels.CommentsPanel(),
        ],
    )


@register_model_view(BGPPeergroupAddressFamily, 'add', detail=False)
@register_model_view(BGPPeergroupAddressFamily, 'edit')
class BGPPeergroupAddressFamilyEditView(generic.ObjectEditView):
    queryset = BGPPeergroupAddressFamily.objects.all()
    form = forms.BGPPeergroupAddressFamilyForm


@register_model_view(BGPPeergroupAddressFamily, 'delete')
class BGPPeergroupAddressFamilyDeleteView(generic.ObjectDeleteView):
    queryset = BGPPeergroupAddressFamily.objects.all()


@register_model_view(BGPPeergroupAddressFamily, 'bulk_import', path='import', detail=False)
class BGPPeergroupAddressFamilyBulkImportView(generic.BulkImportView):
    queryset = BGPPeergroupAddressFamily.objects.all()
    model_form = forms.BGPPeergroupAddressFamilyImportForm


@register_model_view(BGPPeergroupAddressFamily, 'bulk_edit', path='edit', detail=False)
class BGPPeergroupAddressFamilyBulkEditView(generic.BulkEditView):
    queryset = BGPPeergroupAddressFamily.objects.all()
    filterset = filtersets.BGPPeergroupAddressFamilyFilterSet
    table = tables.BGPPeergroupAddressFamilyTable
    form = forms.BGPPeergroupAddressFamilyBulkEditForm


@register_model_view(BGPPeergroupAddressFamily, 'bulk_delete', path='delete', detail=False)
class BGPPeergroupAddressFamilyBulkDeleteView(generic.BulkDeleteView):
    queryset = BGPPeergroupAddressFamily.objects.all()
    filterset = filtersets.BGPPeergroupAddressFamilyFilterSet
    table = tables.BGPPeergroupAddressFamilyTable
