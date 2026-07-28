"""
URL patterns for the Routing Protocols plugin.

Nothing here names a view. Each view class declares its own model with `@register_model_view()`, and this module
simply asks NetBox's registry for the paths belonging to each model. A view therefore cannot be attached to the
wrong model's URL name: the model that owns the name and the model whose queryset the view operates on are the same
object by construction.

This replaces a hand-written path table in which `prefixlistrule_bulk_delete` and `routemaprule_bulk_delete` were
wired to the PrefixList and RouteMap bulk-delete views, causing bulk deletion of *rules* to destroy unrelated
prefix lists and route maps with matching primary keys.
"""

from django.urls import include, path

from utilities.urls import get_model_urls

from . import views  # noqa: F401  (imported for its @register_model_view side effects)

app_name = 'netbox_routing_protocols'

APP_LABEL = 'netbox_routing_protocols'

# Maps each model's URL prefix to its model name. The model name is what get_model_urls() looks up, so the two can
# never drift apart the way a hand-written path table can.
#
# The prefixes deliberately match the REST API's routes in api/urls.py, hyphen for hyphen, so that a UI path and its
# API counterpart differ only by the /api/plugins/routing-protocols prefix.
MODEL_URL_PREFIXES = {
    'static-routes': 'staticroute',
    'prefix-lists': 'prefixlist',
    'prefix-list-rules': 'prefixlistrule',
    'route-maps': 'routemap',
    'route-map-rules': 'routemaprule',
    'bgp-routers': 'bgprouter',
    'bgp-peer-groups': 'bgppeergroup',
    'bgp-peers': 'bgppeer',
    'bgp-address-families': 'bgpaddressfamily',
    'bgp-redistributions': 'bgpaddressfamilyredistribute',
    'bgp-peer-address-families': 'bgppeeraddressfamily',
    'bgp-peer-group-address-families': 'bgppeergroupaddressfamily',
}

urlpatterns = []

for prefix, model_name in MODEL_URL_PREFIXES.items():
    urlpatterns += [
        path(f'{prefix}/', include(get_model_urls(APP_LABEL, model_name, detail=False))),
        path(f'{prefix}/<int:pk>/', include(get_model_urls(APP_LABEL, model_name))),
    ]
