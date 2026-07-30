from utilities.choices import ChoiceSet


class ActionChoices(ChoiceSet):
    """Permit or deny, as used by prefix list and route map rules."""

    ACTION_PERMIT = 'permit'
    ACTION_DENY = 'deny'

    CHOICES = [
        (ACTION_PERMIT, 'Permit', 'green'),
        (ACTION_DENY, 'Deny', 'red'),
    ]


class AddressFamilyChoices(ChoiceSet):
    """
    IP address family, stored as the integer NetBox uses for ``Prefix.family``
    so the two can be compared directly.
    """

    FAMILY_IPV4 = 4
    FAMILY_IPV6 = 6

    CHOICES = [
        (FAMILY_IPV4, 'IPv4'),
        (FAMILY_IPV6, 'IPv6'),
    ]


class BGPAddressFamilyChoices(ChoiceSet):
    """BGP address family identifiers."""

    AFI_IPV4_UNICAST = 'ipv4-unicast'
    AFI_IPV6_UNICAST = 'ipv6-unicast'
    AFI_L2VPN_EVPN = 'l2vpn-evpn'

    CHOICES = [
        (AFI_IPV4_UNICAST, 'IPv4 Unicast', 'blue'),
        (AFI_IPV6_UNICAST, 'IPv6 Unicast', 'purple'),
        (AFI_L2VPN_EVPN, 'L2VPN EVPN', 'orange'),
    ]


class BGPCommunityTypeChoices(ChoiceSet):
    """BGP community formats."""

    TYPE_STANDARD = 'standard'
    TYPE_EXTENDED = 'extended'
    TYPE_LARGE = 'large'

    CHOICES = [
        (TYPE_STANDARD, 'Standard', 'blue'),
        (TYPE_EXTENDED, 'Extended', 'purple'),
        (TYPE_LARGE, 'Large', 'orange'),
    ]


class BGPRedistributeProtocolChoices(ChoiceSet):
    """Source protocols that may be redistributed into a BGP address family."""

    PROTOCOL_CONNECTED = 'connected'
    PROTOCOL_STATIC = 'static'

    CHOICES = [
        (PROTOCOL_CONNECTED, 'Connected', 'green'),
        (PROTOCOL_STATIC, 'Static', 'blue'),
    ]
