import re

from django import forms
from django.db.models import Q
from django.utils.translation import gettext_lazy as _

from dcim.models import Device, Interface
from ipam.models import ASN, VRF, IPAddress, Prefix
from netbox.forms import (
    NetBoxModelBulkEditForm,
    NetBoxModelForm,
    NetBoxModelImportForm,
    PrimaryModelFilterSetForm,
)
from utilities.forms import BOOLEAN_WITH_BLANK_CHOICES
from utilities.forms.fields import (
    CommentField,
    CSVChoiceField,
    CSVModelChoiceField,
    CSVModelMultipleChoiceField,
    DynamicModelChoiceField,
    DynamicModelMultipleChoiceField,
    TagFilterField,
)
from utilities.forms.rendering import FieldSet, TabbedGroups
from utilities.forms.widgets import BulkEditNullBooleanSelect

from netbox_routing_protocols.choices import BGPAddressFamilyChoices, BGPRedistributeProtocolChoices
from netbox_routing_protocols.models import (
    BFDProfile,
    BGPAddressFamily,
    BGPAddressFamilyRedistribute,
    BGPPeer,
    BGPPeerAddressFamily,
    BGPPeergroup,
    BGPPeergroupAddressFamily,
    BGPRouter,
    RouteMap,
)

__all__ = (
    'BGPAddressFamilyBulkEditForm',
    'BGPAddressFamilyFilterForm',
    'BGPAddressFamilyForm',
    'BGPAddressFamilyImportForm',
    'BGPAddressFamilyRedistributeBulkEditForm',
    'BGPAddressFamilyRedistributeFilterForm',
    'BGPAddressFamilyRedistributeForm',
    'BGPAddressFamilyRedistributeImportForm',
    'BGPPeerAddressFamilyBulkEditForm',
    'BGPPeerAddressFamilyFilterForm',
    'BGPPeerAddressFamilyForm',
    'BGPPeerAddressFamilyImportForm',
    'BGPPeerBulkEditForm',
    'BGPPeerFilterForm',
    'BGPPeerForm',
    'BGPPeerImportForm',
    'BGPPeergroupAddressFamilyBulkEditForm',
    'BGPPeergroupAddressFamilyFilterForm',
    'BGPPeergroupAddressFamilyForm',
    'BGPPeergroupAddressFamilyImportForm',
    'BGPPeergroupBulkEditForm',
    'BGPPeergroupFilterForm',
    'BGPPeergroupForm',
    'BGPPeergroupImportForm',
    'BGPRouterBulkEditForm',
    'BGPRouterFilterForm',
    'BGPRouterForm',
    'BGPRouterImportForm',
)

# A peer is identified either by its remote address or, when unnumbered, by its local interface.
# This distinguishes the two forms in a CSV cell without parsing the address itself.
IP_LIKE = re.compile(r'^[0-9a-fA-F.:/]+$')


class BGPRouterCSVMixin(forms.Form):
    """
    Resolves the parent ``bgprouter`` from device and VRF names during CSV import.

    A BGP router is identified by the (device, VRF) pair rather than by any single natural key,
    so it cannot be expressed as a plain ``CSVModelChoiceField``.
    """

    device = CSVModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        to_field_name='name',
        help_text=_('Name of the device hosting the BGP router'),
    )
    vrf = CSVModelChoiceField(
        label=_('VRF'),
        queryset=VRF.objects.all(),
        to_field_name='name',
        help_text=_('Name of the VRF in which the BGP router runs'),
    )

    def clean(self):
        cleaned_data = super().clean()

        device = cleaned_data.get('device')
        vrf = cleaned_data.get('vrf')
        if device and vrf:
            try:
                self.instance.bgprouter = BGPRouter.objects.get(device=device, vrf=vrf)
            except BGPRouter.DoesNotExist as exc:
                raise forms.ValidationError(
                    {
                        'device': _('No BGP router exists for device {device} in VRF {vrf}.').format(
                            device=device, vrf=vrf
                        ),
                    }
                ) from exc

        return cleaned_data

    def _get_validation_exclusions(self):
        # ``bgprouter`` is assigned in clean() rather than by a form field, so Django would
        # otherwise skip the unique constraints which reference it. It stays excluded when the
        # router could not be resolved: clean() has already reported that against `device`, and a
        # model error keyed on `bgprouter` would blow up add_error(), which has no such form field.
        exclude = super()._get_validation_exclusions()
        if self.instance.bgprouter_id:
            exclude.discard('bgprouter')
        return exclude


class BGPPasswordMixin(forms.Form):
    """
    The BGP MD5 key, edited as an ordinary text field.

    It is deliberately visible: the key has to reach device configuration, so
    hiding it in the UI while returning it over the REST and GraphQL APIs would
    be inconsistent without being safer. Store the platform's encrypted or hashed
    representation rather than the raw secret — see the README.
    """

    password = forms.CharField(
        label=_('Password'),
        required=False,
        help_text=_('BGP MD5 authentication key. Prefer your platform’s hashed form over the raw secret.'),
    )


#
# BGP routers
#


class BGPRouterForm(NetBoxModelForm):
    device = DynamicModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        selector=True,
    )
    vrf = DynamicModelChoiceField(
        label=_('VRF'),
        queryset=VRF.objects.all(),
    )
    asn = DynamicModelChoiceField(
        label=_('ASN'),
        queryset=ASN.objects.all(),
        required=False,
    )
    router_id = DynamicModelChoiceField(
        label=_('Router ID'),
        queryset=IPAddress.objects.all(),
        required=False,
        query_params={
            'device_id': '$device',
            'vrf_id': '$vrf',
        },
    )
    comments = CommentField()

    fieldsets = (
        FieldSet('device', 'vrf', 'enable', name=_('BGP Router')),
        FieldSet('asn', 'router_id', name=_('Identity')),
        FieldSet('multipath_relax', 'route_reflection', 'enable_evpn', name=_('Behaviour')),
        FieldSet('description', 'tags', name=_('Attributes')),
    )

    class Meta:
        model = BGPRouter
        fields = (
            'device',
            'vrf',
            'enable',
            'asn',
            'router_id',
            'multipath_relax',
            'route_reflection',
            'enable_evpn',
            'description',
            'comments',
            'tags',
        )


class BGPRouterFilterForm(PrimaryModelFilterSetForm):
    model = BGPRouter

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
    asn_id = DynamicModelMultipleChoiceField(
        label=_('ASN'),
        queryset=ASN.objects.all(),
        required=False,
    )
    router_id_id = DynamicModelMultipleChoiceField(
        label=_('Router ID'),
        queryset=IPAddress.objects.all(),
        required=False,
    )
    enable = forms.NullBooleanField(
        label=_('Enabled'),
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    multipath_relax = forms.NullBooleanField(
        label=_('Multipath Relax'),
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    route_reflection = forms.NullBooleanField(
        label=_('Route Reflection'),
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    enable_evpn = forms.NullBooleanField(
        label=_('Enable EVPN'),
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    tag = TagFilterField(model)

    fieldsets = (
        FieldSet('q', 'filter_id', 'tag'),
        FieldSet('device_id', 'vrf_id', 'enable', name=_('BGP Router')),
        FieldSet('asn_id', 'router_id_id', name=_('Identity')),
        FieldSet('multipath_relax', 'route_reflection', 'enable_evpn', name=_('Behaviour')),
        FieldSet('owner_group_id', 'owner_id', name=_('Ownership')),
    )


class BGPRouterBulkEditForm(NetBoxModelBulkEditForm):
    model = BGPRouter

    vrf = DynamicModelChoiceField(
        label=_('VRF'),
        queryset=VRF.objects.all(),
        required=False,
    )
    asn = DynamicModelChoiceField(
        label=_('ASN'),
        queryset=ASN.objects.all(),
        required=False,
    )
    enable = forms.NullBooleanField(
        label=_('Enabled'),
        required=False,
        widget=BulkEditNullBooleanSelect(),
    )
    multipath_relax = forms.NullBooleanField(
        label=_('Multipath Relax'),
        required=False,
        widget=BulkEditNullBooleanSelect(),
    )
    route_reflection = forms.NullBooleanField(
        label=_('Route Reflection'),
        required=False,
        widget=BulkEditNullBooleanSelect(),
    )
    enable_evpn = forms.NullBooleanField(
        label=_('Enable EVPN'),
        required=False,
        widget=BulkEditNullBooleanSelect(),
    )
    description = forms.CharField(
        label=_('Description'),
        max_length=200,
        required=False,
    )
    comments = CommentField()

    fieldsets = (
        FieldSet('vrf', 'asn', 'enable', name=_('BGP Router')),
        FieldSet('multipath_relax', 'route_reflection', 'enable_evpn', 'description', name=_('Behaviour')),
    )
    nullable_fields = ('asn', 'description', 'comments')


class BGPRouterImportForm(NetBoxModelImportForm):
    device = CSVModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        to_field_name='name',
        help_text=_('Name of the device hosting the BGP router'),
    )
    vrf = CSVModelChoiceField(
        label=_('VRF'),
        queryset=VRF.objects.all(),
        to_field_name='name',
        help_text=_('Name of the VRF in which the BGP router runs'),
    )
    asn = CSVModelChoiceField(
        label=_('ASN'),
        queryset=ASN.objects.all(),
        to_field_name='asn',
        required=False,
        help_text=_('Local autonomous system number'),
    )
    router_id = CSVModelChoiceField(
        label=_('Router ID'),
        queryset=IPAddress.objects.all(),
        to_field_name='address',
        required=False,
        help_text=_('Router ID address, with mask (e.g. 192.0.2.1/32)'),
    )

    fieldsets = (
        FieldSet('id', 'device', 'vrf', 'enable', name=_('BGP Router')),
        FieldSet('asn', 'router_id', name=_('Identity')),
        FieldSet('multipath_relax', 'route_reflection', 'enable_evpn', name=_('Behaviour')),
        FieldSet('description', 'comments', 'tags', name=_('Attributes')),
    )

    class Meta:
        model = BGPRouter
        fields = (
            'device',
            'vrf',
            'enable',
            'asn',
            'router_id',
            'multipath_relax',
            'route_reflection',
            'enable_evpn',
            'description',
            'comments',
            'tags',
        )


#
# BGP peer groups
#


class BGPPeergroupForm(BGPPasswordMixin, NetBoxModelForm):
    bgprouter = DynamicModelChoiceField(
        label=_('BGP Router'),
        queryset=BGPRouter.objects.all(),
        selector=True,
    )
    remote_as = DynamicModelChoiceField(
        label=_('Remote AS'),
        queryset=ASN.objects.all(),
    )
    bfd = DynamicModelChoiceField(
        label=_('BFD Profile'),
        queryset=BFDProfile.objects.all(),
        required=False,
        help_text=_('Enable BFD for this session using the parameters of the referenced profile.'),
    )
    comments = CommentField()

    fieldsets = (
        FieldSet('bgprouter', 'name', 'enable', name=_('Peer Group')),
        FieldSet('remote_as', 'bfd', 'password', name=_('Session')),
        FieldSet('ebgp_multihop', 'ebgp_multihop_ttl', name=_('eBGP Multihop')),
        FieldSet('description', 'tags', name=_('Attributes')),
    )

    class Meta:
        model = BGPPeergroup
        fields = (
            'bgprouter',
            'name',
            'enable',
            'remote_as',
            'bfd',
            'password',
            'ebgp_multihop',
            'ebgp_multihop_ttl',
            'description',
            'comments',
            'tags',
        )


class BGPPeergroupFilterForm(PrimaryModelFilterSetForm):
    model = BGPPeergroup

    bgprouter_id = DynamicModelMultipleChoiceField(
        label=_('BGP Router'),
        queryset=BGPRouter.objects.all(),
        required=False,
        query_params={
            'device_id': '$device_id',
            'vrf_id': '$vrf_id',
        },
    )
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
    remote_as_id = DynamicModelMultipleChoiceField(
        label=_('Remote AS'),
        queryset=ASN.objects.all(),
        required=False,
    )
    enable = forms.NullBooleanField(
        label=_('Enabled'),
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    bfd_id = DynamicModelMultipleChoiceField(
        label=_('BFD Profile'),
        queryset=BFDProfile.objects.all(),
        required=False,
    )
    ebgp_multihop = forms.NullBooleanField(
        label=_('eBGP Multihop'),
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    tag = TagFilterField(model)

    fieldsets = (
        FieldSet('q', 'filter_id', 'tag'),
        FieldSet('device_id', 'vrf_id', 'bgprouter_id', name=_('BGP Router')),
        FieldSet('remote_as_id', 'enable', 'bfd_id', 'ebgp_multihop', name=_('Session')),
        FieldSet('owner_group_id', 'owner_id', name=_('Ownership')),
    )


class BGPPeergroupBulkEditForm(NetBoxModelBulkEditForm):
    model = BGPPeergroup

    bgprouter = DynamicModelChoiceField(
        label=_('BGP Router'),
        queryset=BGPRouter.objects.all(),
        required=False,
    )
    remote_as = DynamicModelChoiceField(
        label=_('Remote AS'),
        queryset=ASN.objects.all(),
        required=False,
    )
    enable = forms.NullBooleanField(
        label=_('Enabled'),
        required=False,
        widget=BulkEditNullBooleanSelect(),
    )
    bfd = DynamicModelChoiceField(
        label=_('BFD Profile'),
        queryset=BFDProfile.objects.all(),
        required=False,
    )
    # Bulk edit never renders an existing value (there is no single instance), but the
    # widget is left non-rendering anyway so no future change can start echoing keys.
    # A blank entry leaves each selected object's key alone; "Set Null" clears it.
    password = forms.CharField(
        label=_('Password'),
        required=False,
        help_text=_("Leave blank to keep each object's current key."),
    )
    ebgp_multihop = forms.NullBooleanField(
        label=_('eBGP Multihop'),
        required=False,
        widget=BulkEditNullBooleanSelect(),
    )
    ebgp_multihop_ttl = forms.IntegerField(
        label=_('eBGP Multihop TTL'),
        min_value=1,
        max_value=255,
        required=False,
    )
    description = forms.CharField(
        label=_('Description'),
        max_length=200,
        required=False,
    )
    comments = CommentField()

    fieldsets = (
        FieldSet('bgprouter', 'remote_as', 'enable', name=_('Peer Group')),
        FieldSet('bfd', 'password', 'ebgp_multihop', 'ebgp_multihop_ttl', 'description', name=_('Session')),
    )
    nullable_fields = ('bfd', 'password', 'ebgp_multihop_ttl', 'description', 'comments')


class BGPPeergroupImportForm(BGPRouterCSVMixin, NetBoxModelImportForm):
    remote_as = CSVModelChoiceField(
        label=_('Remote AS'),
        queryset=ASN.objects.all(),
        to_field_name='asn',
        help_text=_('Remote autonomous system number'),
    )
    bfd = CSVModelChoiceField(
        label=_('BFD Profile'),
        queryset=BFDProfile.objects.all(),
        to_field_name='name',
        required=False,
        help_text=_('Name of the BFD profile applied to this session (blank for none)'),
    )

    fieldsets = (
        FieldSet('id', 'device', 'vrf', 'name', 'enable', name=_('Peer Group')),
        FieldSet('remote_as', 'bfd', 'password', name=_('Session')),
        FieldSet('ebgp_multihop', 'ebgp_multihop_ttl', name=_('eBGP Multihop')),
        FieldSet('description', 'comments', 'tags', name=_('Attributes')),
    )

    class Meta:
        model = BGPPeergroup
        fields = (
            'device',
            'vrf',
            'name',
            'enable',
            'remote_as',
            'bfd',
            'password',
            'ebgp_multihop',
            'ebgp_multihop_ttl',
            'description',
            'comments',
            'tags',
        )


#
# BGP peers
#


class BGPPeerForm(BGPPasswordMixin, NetBoxModelForm):
    bgprouter = DynamicModelChoiceField(
        label=_('BGP Router'),
        queryset=BGPRouter.objects.all(),
        selector=True,
    )
    peergroup = DynamicModelChoiceField(
        label=_('Peer Group'),
        queryset=BGPPeergroup.objects.all(),
        required=False,
        query_params={
            'bgprouter_id': '$bgprouter',
        },
    )
    remote_address = DynamicModelChoiceField(
        label=_('Remote Address'),
        queryset=IPAddress.objects.all(),
        required=False,
        selector=True,
    )
    interface = DynamicModelChoiceField(
        label=_('Interface'),
        queryset=Interface.objects.all(),
        required=False,
        query_params={
            'device_id': '$device',
        },
    )
    device = DynamicModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        required=False,
        selector=True,
        help_text=_('Used only to narrow the interface selection.'),
    )
    remote_as = DynamicModelChoiceField(
        label=_('Remote AS'),
        queryset=ASN.objects.all(),
    )
    bfd = DynamicModelChoiceField(
        label=_('BFD Profile'),
        queryset=BFDProfile.objects.all(),
        required=False,
        help_text=_('Enable BFD for this session using the parameters of the referenced profile.'),
    )
    comments = CommentField()

    fieldsets = (
        FieldSet('bgprouter', 'peergroup', 'enable', name=_('Peer')),
        FieldSet(
            'device',
            TabbedGroups(
                FieldSet('remote_address', name=_('IP Address')),
                FieldSet('interface', name=_('Unnumbered')),
            ),
            name=_('Addressing'),
        ),
        FieldSet('remote_as', 'bfd', 'password', name=_('Session')),
        FieldSet('ebgp_multihop', 'ebgp_multihop_ttl', name=_('eBGP Multihop')),
        FieldSet('description', 'tags', name=_('Attributes')),
    )

    class Meta:
        model = BGPPeer
        fields = (
            'bgprouter',
            'peergroup',
            'enable',
            'remote_address',
            'interface',
            'remote_as',
            'bfd',
            'password',
            'ebgp_multihop',
            'ebgp_multihop_ttl',
            'description',
            'comments',
            'tags',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # `device` is a convenience selector, not a model field, so seed it from the parent router.
        if self.instance.pk:
            self.fields['device'].initial = self.instance.bgprouter.device_id


class BGPPeerFilterForm(PrimaryModelFilterSetForm):
    model = BGPPeer

    bgprouter_id = DynamicModelMultipleChoiceField(
        label=_('BGP Router'),
        queryset=BGPRouter.objects.all(),
        required=False,
        query_params={
            'device_id': '$device_id',
            'vrf_id': '$vrf_id',
        },
    )
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
    peergroup_id = DynamicModelMultipleChoiceField(
        label=_('Peer Group'),
        queryset=BGPPeergroup.objects.all(),
        required=False,
        query_params={
            'bgprouter_id': '$bgprouter_id',
        },
    )
    remote_address_id = DynamicModelMultipleChoiceField(
        label=_('Remote Address'),
        queryset=IPAddress.objects.all(),
        required=False,
    )
    interface_id = DynamicModelMultipleChoiceField(
        label=_('Interface'),
        queryset=Interface.objects.all(),
        required=False,
        query_params={
            'device_id': '$device_id',
        },
    )
    remote_as_id = DynamicModelMultipleChoiceField(
        label=_('Remote AS'),
        queryset=ASN.objects.all(),
        required=False,
    )
    enable = forms.NullBooleanField(
        label=_('Enabled'),
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    bfd_id = DynamicModelMultipleChoiceField(
        label=_('BFD Profile'),
        queryset=BFDProfile.objects.all(),
        required=False,
    )
    ebgp_multihop = forms.NullBooleanField(
        label=_('eBGP Multihop'),
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    tag = TagFilterField(model)

    fieldsets = (
        FieldSet('q', 'filter_id', 'tag'),
        FieldSet('device_id', 'vrf_id', 'bgprouter_id', name=_('BGP Router')),
        FieldSet('peergroup_id', 'remote_address_id', 'interface_id', name=_('Peer')),
        FieldSet('remote_as_id', 'enable', 'bfd_id', 'ebgp_multihop', name=_('Session')),
        FieldSet('owner_group_id', 'owner_id', name=_('Ownership')),
    )


class BGPPeerBulkEditForm(NetBoxModelBulkEditForm):
    model = BGPPeer

    bgprouter = DynamicModelChoiceField(
        label=_('BGP Router'),
        queryset=BGPRouter.objects.all(),
        required=False,
    )
    peergroup = DynamicModelChoiceField(
        label=_('Peer Group'),
        queryset=BGPPeergroup.objects.all(),
        required=False,
        query_params={
            'bgprouter_id': '$bgprouter',
        },
    )
    remote_as = DynamicModelChoiceField(
        label=_('Remote AS'),
        queryset=ASN.objects.all(),
        required=False,
    )
    enable = forms.NullBooleanField(
        label=_('Enabled'),
        required=False,
        widget=BulkEditNullBooleanSelect(),
    )
    bfd = DynamicModelChoiceField(
        label=_('BFD Profile'),
        queryset=BFDProfile.objects.all(),
        required=False,
    )
    # Bulk edit never renders an existing value (there is no single instance), but the
    # widget is left non-rendering anyway so no future change can start echoing keys.
    # A blank entry leaves each selected object's key alone; "Set Null" clears it.
    password = forms.CharField(
        label=_('Password'),
        required=False,
        help_text=_("Leave blank to keep each object's current key."),
    )
    ebgp_multihop = forms.NullBooleanField(
        label=_('eBGP Multihop'),
        required=False,
        widget=BulkEditNullBooleanSelect(),
    )
    ebgp_multihop_ttl = forms.IntegerField(
        label=_('eBGP Multihop TTL'),
        min_value=1,
        max_value=255,
        required=False,
    )
    description = forms.CharField(
        label=_('Description'),
        max_length=200,
        required=False,
    )
    comments = CommentField()

    # `remote_address` and `interface` are mutually exclusive under a CheckConstraint, and are
    # per-peer values in any case, so neither is offered here.
    fieldsets = (
        FieldSet('bgprouter', 'peergroup', 'remote_as', 'enable', name=_('Peer')),
        FieldSet('bfd', 'password', 'ebgp_multihop', 'ebgp_multihop_ttl', 'description', name=_('Session')),
    )
    nullable_fields = ('peergroup', 'bfd', 'password', 'ebgp_multihop_ttl', 'description', 'comments')


class BGPPeerImportForm(BGPRouterCSVMixin, NetBoxModelImportForm):
    remote_address = CSVModelChoiceField(
        label=_('Remote Address'),
        queryset=IPAddress.objects.all(),
        to_field_name='address',
        required=False,
        help_text=_('Remote address, with mask (e.g. 192.0.2.1/32); omit for an unnumbered session'),
    )
    interface = CSVModelChoiceField(
        label=_('Interface'),
        queryset=Interface.objects.all(),
        to_field_name='name',
        required=False,
        help_text=_('Local interface name for an unnumbered session; omit when a remote address is given'),
    )
    peergroup = CSVModelChoiceField(
        label=_('Peer Group'),
        queryset=BGPPeergroup.objects.all(),
        to_field_name='name',
        required=False,
        help_text=_('Name of the assigned peer group'),
    )
    remote_as = CSVModelChoiceField(
        label=_('Remote AS'),
        queryset=ASN.objects.all(),
        to_field_name='asn',
        help_text=_('Remote autonomous system number'),
    )
    bfd = CSVModelChoiceField(
        label=_('BFD Profile'),
        queryset=BFDProfile.objects.all(),
        to_field_name='name',
        required=False,
        help_text=_('Name of the BFD profile applied to this session (blank for none)'),
    )

    fieldsets = (
        FieldSet('id', 'device', 'vrf', 'peergroup', 'enable', name=_('Peer')),
        FieldSet('remote_address', 'interface', name=_('Addressing')),
        FieldSet('remote_as', 'bfd', 'password', name=_('Session')),
        FieldSet('ebgp_multihop', 'ebgp_multihop_ttl', name=_('eBGP Multihop')),
        FieldSet('description', 'comments', 'tags', name=_('Attributes')),
    )

    class Meta:
        model = BGPPeer
        fields = (
            'device',
            'vrf',
            'remote_address',
            'interface',
            'peergroup',
            'enable',
            'remote_as',
            'bfd',
            'password',
            'ebgp_multihop',
            'ebgp_multihop_ttl',
            'description',
            'comments',
            'tags',
        )

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        if not data:
            return

        # Interface and peer group names are only unique within a device or router.
        if device := data.get('device'):
            self.fields['interface'].queryset = Interface.objects.filter(device__name=device)
            peergroups = BGPPeergroup.objects.filter(bgprouter__device__name=device)
            if vrf := data.get('vrf'):
                peergroups = peergroups.filter(bgprouter__vrf__name=vrf)
            self.fields['peergroup'].queryset = peergroups


#
# BGP address families
#


class BGPAddressFamilyForm(NetBoxModelForm):
    bgprouter = DynamicModelChoiceField(
        label=_('BGP Router'),
        queryset=BGPRouter.objects.all(),
        selector=True,
    )
    device = DynamicModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        required=False,
        selector=True,
        help_text=_('Used only to narrow the route map selections.'),
    )
    aggregate_routes = DynamicModelMultipleChoiceField(
        label=_('Aggregate Routes'),
        queryset=Prefix.objects.all(),
        required=False,
    )
    aggregate_route_map = DynamicModelChoiceField(
        label=_('Aggregate Route Map'),
        queryset=RouteMap.objects.all(),
        required=False,
        query_params={
            'available_on_device': '$device',
        },
    )
    networks = DynamicModelMultipleChoiceField(
        label=_('Network Statements'),
        queryset=Prefix.objects.all(),
        required=False,
    )
    network_route_map = DynamicModelChoiceField(
        label=_('Network Route Map'),
        queryset=RouteMap.objects.all(),
        required=False,
        query_params={
            'available_on_device': '$device',
        },
    )
    comments = CommentField()

    fieldsets = (
        FieldSet('bgprouter', 'family', 'enable', 'export_to_evpn', name=_('Address Family')),
        FieldSet('device', name=_('Route Map Scope')),
        FieldSet('aggregate_routes', 'aggregate_route_map', name=_('Aggregation')),
        FieldSet('networks', 'network_route_map', name=_('Origination')),
        FieldSet('description', 'tags', name=_('Attributes')),
    )

    class Meta:
        model = BGPAddressFamily
        fields = (
            'bgprouter',
            'family',
            'enable',
            'aggregate_routes',
            'aggregate_route_map',
            'networks',
            'network_route_map',
            'export_to_evpn',
            'description',
            'comments',
            'tags',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # `device` is a convenience selector, not a model field, so seed it from the parent router.
        if self.instance.pk:
            self.fields['device'].initial = self.instance.bgprouter.device_id


class BGPAddressFamilyFilterForm(PrimaryModelFilterSetForm):
    model = BGPAddressFamily

    bgprouter_id = DynamicModelMultipleChoiceField(
        label=_('BGP Router'),
        queryset=BGPRouter.objects.all(),
        required=False,
        query_params={
            'device_id': '$device_id',
            'vrf_id': '$vrf_id',
        },
    )
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
    family = forms.MultipleChoiceField(
        label=_('Address Family'),
        choices=BGPAddressFamilyChoices,
        required=False,
    )
    aggregate_route_map_id = DynamicModelMultipleChoiceField(
        label=_('Aggregate Route Map'),
        queryset=RouteMap.objects.all(),
        required=False,
    )
    network_route_map_id = DynamicModelMultipleChoiceField(
        label=_('Network Route Map'),
        queryset=RouteMap.objects.all(),
        required=False,
    )
    aggregate_route_id = DynamicModelMultipleChoiceField(
        label=_('Aggregate Route'),
        queryset=Prefix.objects.all(),
        required=False,
    )
    network_id = DynamicModelMultipleChoiceField(
        label=_('Network'),
        queryset=Prefix.objects.all(),
        required=False,
    )
    enable = forms.NullBooleanField(
        label=_('Enabled'),
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    export_to_evpn = forms.NullBooleanField(
        label=_('Export to EVPN'),
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    tag = TagFilterField(model)

    fieldsets = (
        FieldSet('q', 'filter_id', 'tag'),
        FieldSet('device_id', 'vrf_id', 'bgprouter_id', name=_('BGP Router')),
        FieldSet('family', 'enable', 'export_to_evpn', name=_('Address Family')),
        FieldSet('aggregate_route_id', 'network_id', name=_('Origination')),
        FieldSet('aggregate_route_map_id', 'network_route_map_id', name=_('Policy')),
        FieldSet('owner_group_id', 'owner_id', name=_('Ownership')),
    )


class BGPAddressFamilyBulkEditForm(NetBoxModelBulkEditForm):
    model = BGPAddressFamily

    bgprouter = DynamicModelChoiceField(
        label=_('BGP Router'),
        queryset=BGPRouter.objects.all(),
        required=False,
    )
    aggregate_route_map = DynamicModelChoiceField(
        label=_('Aggregate Route Map'),
        queryset=RouteMap.objects.all(),
        required=False,
    )
    network_route_map = DynamicModelChoiceField(
        label=_('Network Route Map'),
        queryset=RouteMap.objects.all(),
        required=False,
    )
    enable = forms.NullBooleanField(
        label=_('Enabled'),
        required=False,
        widget=BulkEditNullBooleanSelect(),
    )
    export_to_evpn = forms.NullBooleanField(
        label=_('Export to EVPN'),
        required=False,
        widget=BulkEditNullBooleanSelect(),
    )
    description = forms.CharField(
        label=_('Description'),
        max_length=200,
        required=False,
    )
    comments = CommentField()

    fieldsets = (
        FieldSet('bgprouter', 'enable', 'export_to_evpn', name=_('Address Family')),
        FieldSet('aggregate_route_map', 'network_route_map', 'description', name=_('Policy')),
    )
    nullable_fields = ('aggregate_route_map', 'network_route_map', 'description', 'comments')


class BGPAddressFamilyImportForm(BGPRouterCSVMixin, NetBoxModelImportForm):
    family = CSVChoiceField(
        label=_('Address Family'),
        choices=BGPAddressFamilyChoices,
        help_text=_('BGP address family identifier'),
    )
    aggregate_routes = CSVModelMultipleChoiceField(
        label=_('Aggregate Routes'),
        queryset=Prefix.objects.all(),
        to_field_name='prefix',
        required=False,
        help_text=_('Comma-separated list of aggregate prefixes, encased in double quotes'),
    )
    aggregate_route_map = CSVModelChoiceField(
        label=_('Aggregate Route Map'),
        queryset=RouteMap.objects.all(),
        to_field_name='name',
        required=False,
        help_text=_('Name of the aggregation route map (must belong to the same device)'),
    )
    networks = CSVModelMultipleChoiceField(
        label=_('Network Statements'),
        queryset=Prefix.objects.all(),
        to_field_name='prefix',
        required=False,
        help_text=_('Comma-separated list of network prefixes, encased in double quotes'),
    )
    network_route_map = CSVModelChoiceField(
        label=_('Network Route Map'),
        queryset=RouteMap.objects.all(),
        to_field_name='name',
        required=False,
        help_text=_('Name of the network route map (must belong to the same device)'),
    )

    fieldsets = (
        FieldSet('id', 'device', 'vrf', 'family', 'enable', 'export_to_evpn', name=_('Address Family')),
        FieldSet('aggregate_routes', 'aggregate_route_map', name=_('Aggregation')),
        FieldSet('networks', 'network_route_map', name=_('Origination')),
        FieldSet('description', 'comments', 'tags', name=_('Attributes')),
    )

    class Meta:
        model = BGPAddressFamily
        fields = (
            'device',
            'vrf',
            'family',
            'enable',
            'aggregate_routes',
            'aggregate_route_map',
            'networks',
            'network_route_map',
            'export_to_evpn',
            'description',
            'comments',
            'tags',
        )

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        # Route map names are only unique per device; shared route maps (no device)
        # remain selectable from any device.
        if data and (device := data.get('device')):
            route_maps = RouteMap.objects.filter(Q(device__name=device) | Q(device__isnull=True))
            self.fields['aggregate_route_map'].queryset = route_maps
            self.fields['network_route_map'].queryset = route_maps


#
# BGP redistributions
#


class BGPAddressFamilyRedistributeForm(NetBoxModelForm):
    family = DynamicModelChoiceField(
        label=_('Address Family'),
        queryset=BGPAddressFamily.objects.all(),
        selector=True,
    )
    device = DynamicModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        required=False,
        selector=True,
        help_text=_('Used only to narrow the route map selection.'),
    )
    route_map = DynamicModelChoiceField(
        label=_('Route Map'),
        queryset=RouteMap.objects.all(),
        required=False,
        query_params={
            'available_on_device': '$device',
        },
    )
    comments = CommentField()

    fieldsets = (
        FieldSet('family', 'protocol', 'enable', name=_('Redistribution')),
        FieldSet('device', 'route_map', name=_('Policy')),
        FieldSet('description', 'tags', name=_('Attributes')),
    )

    class Meta:
        model = BGPAddressFamilyRedistribute
        fields = ('family', 'protocol', 'enable', 'route_map', 'description', 'comments', 'tags')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # `device` is a convenience selector, not a model field, so seed it from the parent router.
        if self.instance.pk:
            self.fields['device'].initial = self.instance.family.bgprouter.device_id


class BGPAddressFamilyRedistributeFilterForm(PrimaryModelFilterSetForm):
    model = BGPAddressFamilyRedistribute

    family_id = DynamicModelMultipleChoiceField(
        label=_('Address Family'),
        queryset=BGPAddressFamily.objects.all(),
        required=False,
    )
    bgprouter_id = DynamicModelMultipleChoiceField(
        label=_('BGP Router'),
        queryset=BGPRouter.objects.all(),
        required=False,
        query_params={
            'device_id': '$device_id',
        },
    )
    device_id = DynamicModelMultipleChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        required=False,
    )
    route_map_id = DynamicModelMultipleChoiceField(
        label=_('Route Map'),
        queryset=RouteMap.objects.all(),
        required=False,
    )
    protocol = forms.MultipleChoiceField(
        label=_('Protocol'),
        choices=BGPRedistributeProtocolChoices,
        required=False,
    )
    enable = forms.NullBooleanField(
        label=_('Enabled'),
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    tag = TagFilterField(model)

    fieldsets = (
        FieldSet('q', 'filter_id', 'tag'),
        FieldSet('device_id', 'bgprouter_id', 'family_id', name=_('Address Family')),
        FieldSet('protocol', 'enable', 'route_map_id', name=_('Redistribution')),
        FieldSet('owner_group_id', 'owner_id', name=_('Ownership')),
    )


class BGPAddressFamilyRedistributeBulkEditForm(NetBoxModelBulkEditForm):
    model = BGPAddressFamilyRedistribute

    family = DynamicModelChoiceField(
        label=_('Address Family'),
        queryset=BGPAddressFamily.objects.all(),
        required=False,
    )
    protocol = forms.ChoiceField(
        label=_('Protocol'),
        choices=BGPRedistributeProtocolChoices,
        required=False,
    )
    route_map = DynamicModelChoiceField(
        label=_('Route Map'),
        queryset=RouteMap.objects.all(),
        required=False,
    )
    enable = forms.NullBooleanField(
        label=_('Enabled'),
        required=False,
        widget=BulkEditNullBooleanSelect(),
    )
    description = forms.CharField(
        label=_('Description'),
        max_length=200,
        required=False,
    )
    comments = CommentField()

    fieldsets = (FieldSet('family', 'protocol', 'enable', 'route_map', 'description'),)
    nullable_fields = ('route_map', 'description', 'comments')


class BGPAddressFamilyRedistributeImportForm(NetBoxModelImportForm):
    device = CSVModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        to_field_name='name',
        help_text=_('Name of the device hosting the BGP router'),
    )
    vrf = CSVModelChoiceField(
        label=_('VRF'),
        queryset=VRF.objects.all(),
        to_field_name='name',
        help_text=_('Name of the VRF in which the BGP router runs'),
    )
    family = CSVModelChoiceField(
        label=_('Address Family'),
        queryset=BGPAddressFamily.objects.all(),
        to_field_name='family',
        help_text=_('Address family identifier of the parent, e.g. ipv4-unicast'),
    )
    protocol = CSVChoiceField(
        label=_('Protocol'),
        choices=BGPRedistributeProtocolChoices,
        help_text=_('Source protocol to redistribute'),
    )
    route_map = CSVModelChoiceField(
        label=_('Route Map'),
        queryset=RouteMap.objects.all(),
        to_field_name='name',
        required=False,
        help_text=_('Name of the applied route map (must belong to the same device)'),
    )

    fieldsets = (
        FieldSet('id', 'device', 'vrf', 'family', name=_('Address Family')),
        FieldSet('protocol', 'enable', 'route_map', name=_('Redistribution')),
        FieldSet('description', 'comments', 'tags', name=_('Attributes')),
    )

    class Meta:
        model = BGPAddressFamilyRedistribute
        fields = (
            'device',
            'vrf',
            'family',
            'protocol',
            'enable',
            'route_map',
            'description',
            'comments',
            'tags',
        )

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        if not data:
            return

        if device := data.get('device'):
            families = BGPAddressFamily.objects.filter(bgprouter__device__name=device)
            if vrf := data.get('vrf'):
                families = families.filter(bgprouter__vrf__name=vrf)
            self.fields['family'].queryset = families
            self.fields['route_map'].queryset = RouteMap.objects.filter(Q(device__name=device) | Q(device__isnull=True))


#
# Peer and peer group address families
#


class BGPPeerAddressFamilyForm(NetBoxModelForm):
    peer = DynamicModelChoiceField(
        label=_('BGP Peer'),
        queryset=BGPPeer.objects.all(),
        selector=True,
    )
    device = DynamicModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        required=False,
        selector=True,
        help_text=_('Used only to narrow the policy selections.'),
    )
    inbound_policy = DynamicModelChoiceField(
        label=_('Inbound Policy'),
        queryset=RouteMap.objects.all(),
        required=False,
        query_params={
            'available_on_device': '$device',
        },
    )
    outbound_policy = DynamicModelChoiceField(
        label=_('Outbound Policy'),
        queryset=RouteMap.objects.all(),
        required=False,
        query_params={
            'available_on_device': '$device',
        },
    )
    comments = CommentField()

    fieldsets = (
        FieldSet('peer', 'family', 'enable', name=_('Peer Address Family')),
        FieldSet('device', 'inbound_policy', 'outbound_policy', name=_('Policy')),
        FieldSet('soft_reconfiguration', 'default_originate', 'route_reflector_client', name=_('Behaviour')),
        FieldSet('description', 'tags', name=_('Attributes')),
    )

    class Meta:
        model = BGPPeerAddressFamily
        fields = (
            'peer',
            'family',
            'enable',
            'inbound_policy',
            'outbound_policy',
            'soft_reconfiguration',
            'default_originate',
            'route_reflector_client',
            'description',
            'comments',
            'tags',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # `device` is a convenience selector, not a model field, so seed it from the parent router.
        if self.instance.pk:
            self.fields['device'].initial = self.instance.peer.bgprouter.device_id


class BGPPeerAddressFamilyFilterForm(PrimaryModelFilterSetForm):
    model = BGPPeerAddressFamily

    peer_id = DynamicModelMultipleChoiceField(
        label=_('BGP Peer'),
        queryset=BGPPeer.objects.all(),
        required=False,
        query_params={
            'bgprouter_id': '$bgprouter_id',
        },
    )
    bgprouter_id = DynamicModelMultipleChoiceField(
        label=_('BGP Router'),
        queryset=BGPRouter.objects.all(),
        required=False,
        query_params={
            'device_id': '$device_id',
        },
    )
    device_id = DynamicModelMultipleChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        required=False,
    )
    family = forms.MultipleChoiceField(
        label=_('Address Family'),
        choices=BGPAddressFamilyChoices,
        required=False,
    )
    inbound_policy_id = DynamicModelMultipleChoiceField(
        label=_('Inbound Policy'),
        queryset=RouteMap.objects.all(),
        required=False,
    )
    outbound_policy_id = DynamicModelMultipleChoiceField(
        label=_('Outbound Policy'),
        queryset=RouteMap.objects.all(),
        required=False,
    )
    enable = forms.NullBooleanField(
        label=_('Enabled'),
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    soft_reconfiguration = forms.NullBooleanField(
        label=_('Soft Reconfiguration'),
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    default_originate = forms.NullBooleanField(
        label=_('Default Originate'),
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    route_reflector_client = forms.NullBooleanField(
        label=_('Route Reflector Client'),
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    tag = TagFilterField(model)

    fieldsets = (
        FieldSet('q', 'filter_id', 'tag'),
        FieldSet('device_id', 'bgprouter_id', 'peer_id', name=_('Peer')),
        FieldSet('family', 'enable', name=_('Address Family')),
        FieldSet('inbound_policy_id', 'outbound_policy_id', name=_('Policy')),
        FieldSet(
            'soft_reconfiguration',
            'default_originate',
            'route_reflector_client',
            name=_('Behaviour'),
        ),
        FieldSet('owner_group_id', 'owner_id', name=_('Ownership')),
    )


class BGPPeerAddressFamilyBulkEditForm(NetBoxModelBulkEditForm):
    model = BGPPeerAddressFamily

    peer = DynamicModelChoiceField(
        label=_('BGP Peer'),
        queryset=BGPPeer.objects.all(),
        required=False,
    )
    inbound_policy = DynamicModelChoiceField(
        label=_('Inbound Policy'),
        queryset=RouteMap.objects.all(),
        required=False,
    )
    outbound_policy = DynamicModelChoiceField(
        label=_('Outbound Policy'),
        queryset=RouteMap.objects.all(),
        required=False,
    )
    enable = forms.NullBooleanField(
        label=_('Enabled'),
        required=False,
        widget=BulkEditNullBooleanSelect(),
    )
    soft_reconfiguration = forms.NullBooleanField(
        label=_('Soft Reconfiguration'),
        required=False,
        widget=BulkEditNullBooleanSelect(),
    )
    default_originate = forms.NullBooleanField(
        label=_('Default Originate'),
        required=False,
        widget=BulkEditNullBooleanSelect(),
    )
    route_reflector_client = forms.NullBooleanField(
        label=_('Route Reflector Client'),
        required=False,
        widget=BulkEditNullBooleanSelect(),
    )
    description = forms.CharField(
        label=_('Description'),
        max_length=200,
        required=False,
    )
    comments = CommentField()

    fieldsets = (
        FieldSet('peer', 'enable', 'description', name=_('Peer Address Family')),
        FieldSet('inbound_policy', 'outbound_policy', name=_('Policy')),
        FieldSet(
            'soft_reconfiguration',
            'default_originate',
            'route_reflector_client',
            name=_('Behaviour'),
        ),
    )
    nullable_fields = ('inbound_policy', 'outbound_policy', 'description', 'comments')


class BGPPeerAddressFamilyImportForm(NetBoxModelImportForm):
    device = CSVModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        to_field_name='name',
        help_text=_('Name of the device hosting the BGP router'),
    )
    vrf = CSVModelChoiceField(
        label=_('VRF'),
        queryset=VRF.objects.all(),
        to_field_name='name',
        help_text=_('Name of the VRF in which the BGP router runs'),
    )
    peer = CSVModelChoiceField(
        label=_('BGP Peer'),
        queryset=BGPPeer.objects.all(),
        to_field_name='remote_address__address',
        help_text=_(
            'Remote address of the peer, with mask (e.g. 192.0.2.1/32); for an unnumbered peer, '
            'the local interface name instead'
        ),
    )
    family = CSVChoiceField(
        label=_('Address Family'),
        choices=BGPAddressFamilyChoices,
        help_text=_('BGP address family identifier'),
    )
    inbound_policy = CSVModelChoiceField(
        label=_('Inbound Policy'),
        queryset=RouteMap.objects.all(),
        to_field_name='name',
        required=False,
        help_text=_('Name of the inbound route map (must belong to the same device)'),
    )
    outbound_policy = CSVModelChoiceField(
        label=_('Outbound Policy'),
        queryset=RouteMap.objects.all(),
        to_field_name='name',
        required=False,
        help_text=_('Name of the outbound route map (must belong to the same device)'),
    )

    fieldsets = (
        FieldSet('id', 'device', 'vrf', 'peer', name=_('Peer')),
        FieldSet('family', 'enable', name=_('Address Family')),
        FieldSet('inbound_policy', 'outbound_policy', name=_('Policy')),
        FieldSet(
            'soft_reconfiguration',
            'default_originate',
            'route_reflector_client',
            name=_('Behaviour'),
        ),
        FieldSet('description', 'comments', 'tags', name=_('Attributes')),
    )

    class Meta:
        model = BGPPeerAddressFamily
        fields = (
            'device',
            'vrf',
            'peer',
            'family',
            'enable',
            'inbound_policy',
            'outbound_policy',
            'soft_reconfiguration',
            'default_originate',
            'route_reflector_client',
            'description',
            'comments',
            'tags',
        )

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        if not data:
            return

        peers = BGPPeer.objects.all()
        if device := data.get('device'):
            peers = peers.filter(bgprouter__device__name=device)
            route_maps = RouteMap.objects.filter(Q(device__name=device) | Q(device__isnull=True))
            self.fields['inbound_policy'].queryset = route_maps
            self.fields['outbound_policy'].queryset = route_maps
        if vrf := data.get('vrf'):
            peers = peers.filter(bgprouter__vrf__name=vrf)
        self.fields['peer'].queryset = peers

        # An unnumbered peer carries no address, so fall back to matching on the interface name.
        if not IP_LIKE.match(str(data.get('peer') or '')):
            self.fields['peer'].to_field_name = 'interface__name'


class BGPPeergroupAddressFamilyForm(NetBoxModelForm):
    peergroup = DynamicModelChoiceField(
        label=_('BGP Peer Group'),
        queryset=BGPPeergroup.objects.all(),
        selector=True,
    )
    device = DynamicModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        required=False,
        selector=True,
        help_text=_('Used only to narrow the policy selections.'),
    )
    inbound_policy = DynamicModelChoiceField(
        label=_('Inbound Policy'),
        queryset=RouteMap.objects.all(),
        required=False,
        query_params={
            'available_on_device': '$device',
        },
    )
    outbound_policy = DynamicModelChoiceField(
        label=_('Outbound Policy'),
        queryset=RouteMap.objects.all(),
        required=False,
        query_params={
            'available_on_device': '$device',
        },
    )
    comments = CommentField()

    fieldsets = (
        FieldSet('peergroup', 'family', 'enable', name=_('Peer Group Address Family')),
        FieldSet('device', 'inbound_policy', 'outbound_policy', name=_('Policy')),
        FieldSet('soft_reconfiguration', 'default_originate', 'route_reflector_client', name=_('Behaviour')),
        FieldSet('description', 'tags', name=_('Attributes')),
    )

    class Meta:
        model = BGPPeergroupAddressFamily
        fields = (
            'peergroup',
            'family',
            'enable',
            'inbound_policy',
            'outbound_policy',
            'soft_reconfiguration',
            'default_originate',
            'route_reflector_client',
            'description',
            'comments',
            'tags',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # `device` is a convenience selector, not a model field, so seed it from the parent router.
        if self.instance.pk:
            self.fields['device'].initial = self.instance.peergroup.bgprouter.device_id


class BGPPeergroupAddressFamilyFilterForm(PrimaryModelFilterSetForm):
    model = BGPPeergroupAddressFamily

    peergroup_id = DynamicModelMultipleChoiceField(
        label=_('BGP Peer Group'),
        queryset=BGPPeergroup.objects.all(),
        required=False,
        query_params={
            'bgprouter_id': '$bgprouter_id',
        },
    )
    bgprouter_id = DynamicModelMultipleChoiceField(
        label=_('BGP Router'),
        queryset=BGPRouter.objects.all(),
        required=False,
        query_params={
            'device_id': '$device_id',
        },
    )
    device_id = DynamicModelMultipleChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        required=False,
    )
    family = forms.MultipleChoiceField(
        label=_('Address Family'),
        choices=BGPAddressFamilyChoices,
        required=False,
    )
    inbound_policy_id = DynamicModelMultipleChoiceField(
        label=_('Inbound Policy'),
        queryset=RouteMap.objects.all(),
        required=False,
    )
    outbound_policy_id = DynamicModelMultipleChoiceField(
        label=_('Outbound Policy'),
        queryset=RouteMap.objects.all(),
        required=False,
    )
    enable = forms.NullBooleanField(
        label=_('Enabled'),
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    soft_reconfiguration = forms.NullBooleanField(
        label=_('Soft Reconfiguration'),
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    default_originate = forms.NullBooleanField(
        label=_('Default Originate'),
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    route_reflector_client = forms.NullBooleanField(
        label=_('Route Reflector Client'),
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    tag = TagFilterField(model)

    fieldsets = (
        FieldSet('q', 'filter_id', 'tag'),
        FieldSet('device_id', 'bgprouter_id', 'peergroup_id', name=_('Peer Group')),
        FieldSet('family', 'enable', name=_('Address Family')),
        FieldSet('inbound_policy_id', 'outbound_policy_id', name=_('Policy')),
        FieldSet(
            'soft_reconfiguration',
            'default_originate',
            'route_reflector_client',
            name=_('Behaviour'),
        ),
        FieldSet('owner_group_id', 'owner_id', name=_('Ownership')),
    )


class BGPPeergroupAddressFamilyBulkEditForm(NetBoxModelBulkEditForm):
    model = BGPPeergroupAddressFamily

    peergroup = DynamicModelChoiceField(
        label=_('BGP Peer Group'),
        queryset=BGPPeergroup.objects.all(),
        required=False,
    )
    inbound_policy = DynamicModelChoiceField(
        label=_('Inbound Policy'),
        queryset=RouteMap.objects.all(),
        required=False,
    )
    outbound_policy = DynamicModelChoiceField(
        label=_('Outbound Policy'),
        queryset=RouteMap.objects.all(),
        required=False,
    )
    enable = forms.NullBooleanField(
        label=_('Enabled'),
        required=False,
        widget=BulkEditNullBooleanSelect(),
    )
    soft_reconfiguration = forms.NullBooleanField(
        label=_('Soft Reconfiguration'),
        required=False,
        widget=BulkEditNullBooleanSelect(),
    )
    default_originate = forms.NullBooleanField(
        label=_('Default Originate'),
        required=False,
        widget=BulkEditNullBooleanSelect(),
    )
    route_reflector_client = forms.NullBooleanField(
        label=_('Route Reflector Client'),
        required=False,
        widget=BulkEditNullBooleanSelect(),
    )
    description = forms.CharField(
        label=_('Description'),
        max_length=200,
        required=False,
    )
    comments = CommentField()

    fieldsets = (
        FieldSet('peergroup', 'enable', 'description', name=_('Peer Group Address Family')),
        FieldSet('inbound_policy', 'outbound_policy', name=_('Policy')),
        FieldSet(
            'soft_reconfiguration',
            'default_originate',
            'route_reflector_client',
            name=_('Behaviour'),
        ),
    )
    nullable_fields = ('inbound_policy', 'outbound_policy', 'description', 'comments')


class BGPPeergroupAddressFamilyImportForm(NetBoxModelImportForm):
    device = CSVModelChoiceField(
        label=_('Device'),
        queryset=Device.objects.all(),
        to_field_name='name',
        help_text=_('Name of the device hosting the BGP router'),
    )
    vrf = CSVModelChoiceField(
        label=_('VRF'),
        queryset=VRF.objects.all(),
        to_field_name='name',
        help_text=_('Name of the VRF in which the BGP router runs'),
    )
    peergroup = CSVModelChoiceField(
        label=_('BGP Peer Group'),
        queryset=BGPPeergroup.objects.all(),
        to_field_name='name',
        help_text=_('Name of the parent peer group'),
    )
    family = CSVChoiceField(
        label=_('Address Family'),
        choices=BGPAddressFamilyChoices,
        help_text=_('BGP address family identifier'),
    )
    inbound_policy = CSVModelChoiceField(
        label=_('Inbound Policy'),
        queryset=RouteMap.objects.all(),
        to_field_name='name',
        required=False,
        help_text=_('Name of the inbound route map (must belong to the same device)'),
    )
    outbound_policy = CSVModelChoiceField(
        label=_('Outbound Policy'),
        queryset=RouteMap.objects.all(),
        to_field_name='name',
        required=False,
        help_text=_('Name of the outbound route map (must belong to the same device)'),
    )

    fieldsets = (
        FieldSet('id', 'device', 'vrf', 'peergroup', name=_('Peer Group')),
        FieldSet('family', 'enable', name=_('Address Family')),
        FieldSet('inbound_policy', 'outbound_policy', name=_('Policy')),
        FieldSet(
            'soft_reconfiguration',
            'default_originate',
            'route_reflector_client',
            name=_('Behaviour'),
        ),
        FieldSet('description', 'comments', 'tags', name=_('Attributes')),
    )

    class Meta:
        model = BGPPeergroupAddressFamily
        fields = (
            'device',
            'vrf',
            'peergroup',
            'family',
            'enable',
            'inbound_policy',
            'outbound_policy',
            'soft_reconfiguration',
            'default_originate',
            'route_reflector_client',
            'description',
            'comments',
            'tags',
        )

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        if not data:
            return

        peergroups = BGPPeergroup.objects.all()
        if device := data.get('device'):
            peergroups = peergroups.filter(bgprouter__device__name=device)
            route_maps = RouteMap.objects.filter(Q(device__name=device) | Q(device__isnull=True))
            self.fields['inbound_policy'].queryset = route_maps
            self.fields['outbound_policy'].queryset = route_maps
        if vrf := data.get('vrf'):
            peergroups = peergroups.filter(bgprouter__vrf__name=vrf)
        self.fields['peergroup'].queryset = peergroups
