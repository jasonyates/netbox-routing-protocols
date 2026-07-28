"""
Shared view helpers.

The only thing here is the "add a child object" button used by the child-object tabs. NetBox 4.6 renders a panel's
`AddObject` action (`netbox.ui.actions.AddObject`) with pre-filled URL parameters, but that machinery applies to
panels inside a detail-view `layout`, not to the button row above an `ObjectChildrenView` tab. For tabs the
equivalent hook is `netbox.object_actions.ObjectAction`, which is pure Python and reuses NetBox's own
`buttons/add.html` — so the pre-filled Add button needs no plugin templates at all.
"""

from urllib.parse import urlencode

from django.urls.exceptions import NoReverseMatch
from django.utils.translation import gettext_lazy as _

from netbox.object_actions import ObjectAction
from utilities.views import get_action_url

__all__ = ('AddChildObject', 'add_child_object')


class AddChildObject(ObjectAction):
    """
    An "Add" button rendered above an `ObjectChildrenView` table which links to the *child* model's add view with the
    parent object pre-selected.

    `ObjectChildrenView.get_permitted_actions()` resolves `permissions_required` against the view's `child_model`, so
    the button is shown only to users who may add the child object — never based on the parent's permissions.

    Attributes:
        child_model: The model class being added (NOT the parent model the view is attached to)
        parent_field: Name of the child model's form field which should be pre-populated with the parent's PK
        extra_params: Additional URL parameters. Values may be callables accepting the parent instance.
    """

    name = 'add'
    label = _('Add')
    template_name = 'buttons/add.html'
    permissions_required = {'add'}

    child_model = None
    parent_field = None
    extra_params = {}

    @classmethod
    def get_url(cls, obj):
        # `obj` is the *parent* instance, so resolve against the child model explicitly.
        try:
            return get_action_url(cls.child_model, action='add')
        except NoReverseMatch:
            return None

    @classmethod
    def get_context(cls, context, obj):
        url = cls.get_url(obj)
        if url is None:
            return {}

        params = {cls.parent_field: obj.pk}
        for key, value in cls.extra_params.items():
            resolved = value(obj) if callable(value) else value
            if resolved is not None:
                params[key] = resolved
        if return_url := context.get('return_url'):
            params['return_url'] = return_url

        # `buttons/add.html` renders `url` verbatim, so the parameters are baked into it.
        return {'url': f'{url}?{urlencode(params)}'}


def add_child_object(model, parent_field, label=None, extra_params=None):
    """
    Build an `AddChildObject` subclass bound to a specific child model and parent field.

    Args:
        model: The child model class to be added
        parent_field: Name of the child's form field to pre-populate with the parent's PK
        label: Button text (defaults to "Add")
        extra_params: Additional URL parameters; values may be callables accepting the parent instance
    """
    return type(
        f'Add{model.__name__}',
        (AddChildObject,),
        {
            'child_model': model,
            'parent_field': parent_field,
            'extra_params': extra_params or {},
            'label': label or _('Add'),
        },
    )
