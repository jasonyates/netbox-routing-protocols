from netbox.plugins import PluginConfig

from .version import __version__


class RoutingProtocolsConfig(PluginConfig):
    name = 'netbox_routing_protocols'
    verbose_name = 'Routing Protocols'
    description = 'Model static routes, routing policy and BGP configuration in NetBox'
    version = __version__
    author = 'Jason Yates'
    author_email = 'me@jasonyates.co.uk'
    base_url = 'routing-protocols'
    min_version = '4.6.0'
    max_version = '4.6.99'

    default_settings = {
        # Create a terminating "deny 9999 / match any" rule whenever a new
        # prefix list or route map is created.
        'create_default_deny_rule': True,
    }

    def ready(self):
        super().ready()
        from . import signals  # noqa: F401


config = RoutingProtocolsConfig
