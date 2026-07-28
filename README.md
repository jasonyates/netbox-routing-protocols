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
- Prefix lists with ordered, sequenced rules
- Prefix list rules matching a prefix, any prefix, or the default route, with `ge`/`le` length bounds
- Route maps with ordered rules matching against prefix lists
- Optional automatic terminating `deny 9999` rule on new prefix lists and route maps

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

Run the migrations and collect static files:

```bash
python manage.py migrate
python manage.py collectstatic --no-input
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

### A note on BGP passwords

`BGPPeer.password` and `BGPPeergroup.password` hold BGP MD5 authentication keys. They are
**write-only** over the REST API — they can be set and updated, but are never returned in a
response. Treat the database as holding secrets and restrict object permissions accordingly.

## Contributing

Issues and pull requests are welcome at
<https://github.com/jasonyates/netbox-routing-protocols>.

## Licence

Apache-2.0. See [LICENSE](LICENSE).
