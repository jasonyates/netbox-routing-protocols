# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] — unreleased

First public release. The plugin has been rebuilt against NetBox 4.6 and a number of
long-standing defects have been corrected. Because field names and API responses have changed,
there is no in-place upgrade path from pre-release internal builds.

### Added
- GraphQL API coverage for all models
- Global search indexes, so routing objects appear in NetBox search
- `create_default_deny_rule` plugin setting to control the automatic terminating deny rule
- CSV bulk import for static routes, prefix lists and route maps
- Tabbed form groups for mutually exclusive fields, replacing custom show/hide JavaScript

### Changed
- Requires NetBox 4.6 and Python 3.12+
- BGP peer and peer-group address families are now separate models with real foreign keys,
  replacing a generic relation
- Models carrying a description and comments now derive from `PrimaryModel`
- Boolean fields are plain booleans rendered with NetBox's boolean column, and are no longer
  nullable
- Foreign keys onto core NetBox models use app-prefixed reverse accessors to avoid collisions
  with other plugins
- Signal receivers moved out of the models module and connected in `ready()`

### Fixed
- Bulk-deleting prefix list rules or route map rules deleted unrelated prefix lists and route
  maps whose primary keys happened to match the selected rules
- `BGPRouter.route_relefection` was misspelled, so the Route Reflection value never rendered on
  the detail page and was silently discarded on CSV import
- `?brief=true` returned an error on most endpoints, which also broke nested serialization of
  prefix lists inside rule responses
- Search (`?q=`) raised an error on static routes and BGP peer address families
- CSV import for static routes, prefix lists and route maps required numeric primary keys
  instead of names
- Static routes with no next hop raised an error when rendered
- A duplicate filter definition on BGP routers silently shadowed the ASN filter
- BGP MD5 passwords were readable through the REST API; they are now write-only

[1.0.0]: https://github.com/jasonyates/netbox-routing-protocols/releases/tag/v1.0.0
