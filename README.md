# NetBox Routing Protocols

A [NetBox](https://netbox.dev) plugin for modelling static routes, routing policy and BGP
configuration alongside the devices and IPAM objects they belong to.

It gives you somewhere to record routing *intent* — which is the piece NetBox leaves to you —
so that config generation, compliance checks and automation can read it back out of the API.

## Features

**Static routing**
- Static routes bound to a device, VRF, prefix and next hop
- Explicit default-route modelling (`0.0.0.0/0` / `::/0`) without needing a placeholder prefix
- A Static Routes tab on the IPAM Prefix view

**Routing policy**
- Prefix lists with ordered, sequenced rules, scoped to a device or shared fleet-wide
- Prefix list rules matching a prefix, any prefix, or the default route, with `ge`/`le` length bounds
- Route maps with ordered rules matching against prefix lists, scoped to a device or shared fleet-wide
- Optional automatic terminating `deny 9999` rule on new prefix lists and route maps
- BFD profiles carrying intervals, detect multiplier, echo and passive mode, referenced from BGP sessions

**BGP**
- BGP routers per device and VRF, with ASN, router ID, AS-path handling and route reflection
- Peers addressed by IP or as unnumbered interface peers
- Peer groups, with peers inheriting group attributes
- Address families (IPv4 unicast, IPv6 unicast, L2VPN EVPN) at router, peer and peer-group level
- Per-address-family inbound and outbound route-map policy
- Network statements, aggregates and protocol redistribution

Every model supports the standard NetBox features: tags, custom fields, change logging,
journaling, export templates, global search, the REST API and the GraphQL API.

## Compatibility

| Plugin | NetBox | Python |
|--------|--------|--------|
| 1.0.x  | 4.6.x  | 3.12+  |

## Installation

Install into your NetBox virtual environment:

```bash
source /opt/netbox/venv/bin/activate
pip install netbox-routing-protocols
```

Add it to `PLUGINS` in `configuration.py`:

```python
PLUGINS = [
    'netbox_routing_protocols',
]
```

Run the migrations:

```bash
python manage.py migrate
```

Add the package to `local_requirements.txt` so it survives a NetBox upgrade:

```bash
echo netbox-routing-protocols >> /opt/netbox/local_requirements.txt
```

Restart NetBox:

```bash
sudo systemctl restart netbox netbox-rq
```

## Configuration

All settings are optional.

```python
PLUGINS_CONFIG = {
    'netbox_routing_protocols': {
        # Create a terminating "deny 9999 / match any" rule whenever a new prefix
        # list or route map is created. Set to False to start them empty.
        'create_default_deny_rule': True,
    },
}
```

## API

REST endpoints are published under `/api/plugins/routing-protocols/`, and all models are
exposed through NetBox's GraphQL API.

```bash
curl -H "Authorization: Token $NETBOX_TOKEN" \
     https://netbox.example.com/api/plugins/routing-protocols/bgp-peers/?device=core-sw-01
```

### ⚠️ BGP passwords are stored and returned in clear

`BGPPeer.password` and `BGPPeergroup.password` hold the BGP MD5 authentication key. The field
is treated like any other: it is **stored as entered and returned verbatim** by the REST API,
the GraphQL API, the change log (and therefore webhook payloads), and the UI.

That is deliberate. The key has to reach device configuration, so config generation must be
able to read it back — a value automation cannot retrieve would defeat the point of recording
it here.

It does mean the value is readable by anyone who can view the object, and by anything holding
`core.view_objectchange`, plus anyone with database or Django shell access.

**Store your platform's hashed or encrypted form, not the raw secret.** Most network operating
systems accept a pre-encrypted key and will render it straight into the configuration:

```
! Cisco IOS — type 7
neighbor 192.0.2.1 password 7 070C285F4D06
! Arista EOS — type 7
neighbor 192.0.2.1 password 7 <encrypted>
! Juniper — $9$ encrypted
set protocols bgp group EXTERNAL neighbor 192.0.2.1 authentication-key "$9$..."
```

Storing that form means NetBox never holds the raw secret, and the value can still be rendered
into config unchanged.

Be aware of what this does and does not buy you. Cisco/Arista type 7 is obfuscation, not
encryption — it is trivially reversible, so it protects against casual exposure (a screenshot,
a shared export, an over-broad API token) rather than against an attacker who obtains the
value. Juniper `$9$` is likewise reversible. If your platform supports a genuinely
non-reversible form, prefer it.

Regardless of which form you store, restrict object permissions to match the sensitivity, and
treat database backups and webhook destinations as carrying secrets.

## Contributing

Issues and pull requests are welcome at
<https://github.com/jasonyates/netbox-routing-protocols>.

### Generating migrations

Generate migrations against the **oldest** supported NetBox release (`min_version` in
`__init__.py`), not whichever one you happen to have installed. `makemigrations` records a
dependency on the newest migration of every app it references, so a migration generated
against a later patch release will fail on earlier ones with:

```
NodeNotFoundError: Migration netbox_routing_protocols.0001_initial dependencies
reference nonexistent parent node ('dcim', '0237_...')
```

CI runs the test matrix against both ends of the supported range, so this is caught before
release rather than by users.

## Licence

Apache-2.0. See [LICENSE](LICENSE).
