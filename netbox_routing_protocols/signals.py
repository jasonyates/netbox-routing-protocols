"""
Signal receivers, connected from ``RoutingProtocolsConfig.ready()``.

These live here rather than in the models module so that importing a model does
not have the side effect of registering handlers.
"""

from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from ipam.models import Prefix
from netbox.plugins import get_plugin_config

from .choices import ActionChoices
from .models import BGPAddressFamily, PrefixList, PrefixListRule, RouteMap, RouteMapRule

# Sequence number used for the terminating rule added to new lists and maps.
DEFAULT_DENY_SEQUENCE = 9999


def _default_deny_enabled() -> bool:
    return get_plugin_config('netbox_routing_protocols', 'create_default_deny_rule')


@receiver(post_save, sender=PrefixList)
def add_prefix_list_default_deny(sender, instance, created, raw=False, **kwargs):
    """Terminate a new prefix list with an explicit deny-any rule."""
    if raw or not created or not _default_deny_enabled():
        return

    PrefixListRule.objects.create(
        prefix_list=instance,
        sequence=DEFAULT_DENY_SEQUENCE,
        action=ActionChoices.ACTION_DENY,
        match_any=True,
        match_default=False,
        prefix=None,
    )


@receiver(post_save, sender=RouteMap)
def add_route_map_default_deny(sender, instance, created, raw=False, **kwargs):
    """Terminate a new route map with an explicit deny-any rule."""
    if raw or not created or not _default_deny_enabled():
        return

    RouteMapRule.objects.create(
        route_map=instance,
        sequence=DEFAULT_DENY_SEQUENCE,
        action=ActionChoices.ACTION_DENY,
        match_any=True,
        prefix_list=None,
    )


@receiver(pre_delete, sender=Prefix)
def record_bgp_prefix_removal(sender, instance, **kwargs):
    """
    Record the removal of a prefix from BGP aggregate and network statements.

    These are many-to-many relations, so deleting a prefix would otherwise drop
    the rows silently with no change log entry — an address family would quietly
    lose network statements. Removing them explicitly here produces a normal
    change log record against each affected address family.
    """
    for field in ('aggregate_routes', 'networks'):
        for address_family in BGPAddressFamily.objects.filter(**{field: instance}):
            address_family.snapshot()
            getattr(address_family, field).remove(instance)
            address_family.save()
