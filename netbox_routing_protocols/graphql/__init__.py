"""
GraphQL API for the Routing Protocols plugin.

NetBox discovers a plugin's GraphQL contribution by importing the plugin's
``graphql`` package and reading the attribute named ``schema`` from it, then
extending its registry with that value. The attribute therefore has to be an
iterable of Strawberry ``Query`` classes, not the ``schema`` submodule -- hence
the assignment below, which deliberately shadows the submodule on this package.
"""

from .schema import Query

__all__ = ('Query', 'schema')

schema = [Query]
