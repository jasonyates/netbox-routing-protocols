"""
REST API URL registration.

NetBox mounts these under ``/api/plugins/<base_url>/`` with the namespace
``plugins-api:netbox_routing_protocols-api``, which is what the serializers'
``url`` fields reverse against.
"""

from netbox.api.routers import NetBoxRouter

from . import views

app_name = 'netbox_routing_protocols'

router = NetBoxRouter()
router.APIRootView = views.RoutingProtocolsRootView

# Static routing
router.register('static-routes', views.StaticRouteViewSet)

# Routing policy
router.register('prefix-lists', views.PrefixListViewSet)
router.register('prefix-list-rules', views.PrefixListRuleViewSet)
router.register('route-maps', views.RouteMapViewSet)
router.register('route-map-rules', views.RouteMapRuleViewSet)

# BFD
router.register('bfd-profiles', views.BFDProfileViewSet)

# BGP
router.register('bgp-routers', views.BGPRouterViewSet)
router.register('bgp-peers', views.BGPPeerViewSet)
router.register('bgp-peer-groups', views.BGPPeergroupViewSet)
router.register('bgp-address-families', views.BGPAddressFamilyViewSet)
router.register('bgp-redistributions', views.BGPAddressFamilyRedistributeViewSet)
router.register('bgp-peer-address-families', views.BGPPeerAddressFamilyViewSet)
router.register('bgp-peer-group-address-families', views.BGPPeergroupAddressFamilyViewSet)

urlpatterns = router.urls
