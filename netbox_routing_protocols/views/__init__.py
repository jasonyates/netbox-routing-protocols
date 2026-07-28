"""
Web UI views.

Every view is bound to its model with `@register_model_view()`, and `urls.py` builds its URL patterns exclusively
from `get_model_urls()`. There is no hand-written URL table, so it is structurally impossible to bind (for example)
a PrefixList bulk-delete view to the `prefixlistrule_bulk_delete` URL name.
"""

from .base import *  # noqa: F403
from .bgp import *  # noqa: F403
from .policy import *  # noqa: F403
from .static import *  # noqa: F403
