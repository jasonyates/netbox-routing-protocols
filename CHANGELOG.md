# Changelog

All notable changes to this project are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- BGP communities ([#1]). `BGPCommunity` records a single community value — standard
  (`ASN:NN` or the well-known names), extended (`rt:`/`soo:`) or large — validated per
  type, unique, and global (communities are estate-wide values). `BGPCommunityList` is a
  named, sequenced list of permit/deny rules referencing communities, scoped to a device
  or shared fleet-wide, with a Rules tab and pre-filled Add button. Full UI, REST API
  (`bgp-communities`, `bgp-community-lists`, `bgp-community-list-rules`), GraphQL, global
  search and CSV import coverage. Matching and setting communities in route maps is
  deliberately out of scope here and tracked by [#2].
- `BFDProfile` model carrying BFD session parameters — TX/RX intervals, detect multiplier,
  echo mode and intervals, passive mode and minimum TTL ([#20]). Profiles follow the shared
  scoping pattern: scoped to a device, or fleet-wide when the device is blank. Full UI,
  REST API (`bfd-profiles`), GraphQL, global search and CSV import coverage.
- Prefix lists and route maps may now be shared fleet-wide by leaving their device blank
  ([#13]). A shared policy object may be referenced from any device's BGP configuration or
  route map rules; names are unique per device and among shared objects. A new
  `available_on_device` API filter returns the objects usable on a device (its own plus
  shared ones), and a `shared` filter selects shared objects alone.

### Changed
- The `bfd` boolean on BGP peers and peer groups is now a nullable foreign key to
  `BFDProfile` ([#20]). A bare "BFD on" cannot render a working configuration — every
  platform needs intervals and a multiplier. The migration preserves intent: peers with
  `bfd=True` are pointed at a shared profile named `default` (all intervals null, meaning
  platform defaults); `bfd=False` becomes null. The REST API field now takes a profile ID,
  and CSV import takes a profile name.
- `BGPRouter.aspath_ignore` renamed to `multipath_relax` ([#5]). The field was inherited
  from an NVUE estate where `aspath-ignore` spells multipath-relax, and the old name and
  help text described a different feature (`bgp bestpath as-path ignore`). Config
  generation consuming this field should now render
  `bgp bestpath as-path multipath-relax` (or the platform equivalent). The default
  remains `True`. API and CSV field names change accordingly.

[#1]: https://github.com/jasonyates/netbox-routing-protocols/issues/1
[#2]: https://github.com/jasonyates/netbox-routing-protocols/issues/2
[#5]: https://github.com/jasonyates/netbox-routing-protocols/issues/5
[#13]: https://github.com/jasonyates/netbox-routing-protocols/issues/13
[#20]: https://github.com/jasonyates/netbox-routing-protocols/issues/20

## [1.0.0] — 2026-07-29

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

### Security
- BGP MD5 authentication keys (`BGPPeer.password`, `BGPPeergroup.password`) are stored and
  returned **in clear** by the REST API, the GraphQL API, the change log and the UI. This is
  deliberate: config generation has to be able to read the key back, so a value automation
  cannot retrieve would defeat the point of recording it. Store your platform's hashed or
  encrypted representation rather than the raw secret, and restrict object permissions
  accordingly — see the README

[1.0.0]: https://github.com/jasonyates/netbox-routing-protocols/releases/tag/v1.0.0
