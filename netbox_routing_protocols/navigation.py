from django.utils.translation import gettext_lazy as _

from netbox.plugins import PluginMenu, PluginMenuButton, PluginMenuItem

__all__ = ('menu',)

APP_LABEL = 'netbox_routing_protocols'


def _menu_item(model_name, label):
    """
    Build a menu item for a model, with Add and Import buttons gated on the model's own permissions.
    """
    return PluginMenuItem(
        link=f'plugins:{APP_LABEL}:{model_name}_list',
        link_text=label,
        permissions=[f'{APP_LABEL}.view_{model_name}'],
        buttons=(
            PluginMenuButton(
                link=f'plugins:{APP_LABEL}:{model_name}_add',
                title=_('Add'),
                icon_class='mdi mdi-plus-thick',
                permissions=[f'{APP_LABEL}.add_{model_name}'],
            ),
            PluginMenuButton(
                link=f'plugins:{APP_LABEL}:{model_name}_bulk_import',
                title=_('Import'),
                icon_class='mdi mdi-upload',
                # Bulk import creates objects, so it is gated on the "add" permission.
                permissions=[f'{APP_LABEL}.add_{model_name}'],
            ),
        ),
    )


menu = PluginMenu(
    label=_('Routing'),
    icon_class='mdi mdi-router',
    groups=(
        (
            _('Static Routes'),
            (_menu_item('staticroute', _('Static Routes')),),
        ),
        (
            _('Routing Policy'),
            (
                _menu_item('prefixlist', _('Prefix Lists')),
                _menu_item('routemap', _('Route Maps')),
            ),
        ),
        (
            _('BGP'),
            (
                _menu_item('bgprouter', _('Routers')),
                _menu_item('bgppeer', _('Peers')),
                _menu_item('bgppeergroup', _('Peer Groups')),
                _menu_item('bgpaddressfamily', _('Address Families')),
                _menu_item('bgpaddressfamilyredistribute', _('Redistributions')),
            ),
        ),
    ),
)
