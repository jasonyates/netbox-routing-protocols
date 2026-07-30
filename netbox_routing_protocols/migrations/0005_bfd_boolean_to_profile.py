"""
Replace the ``bfd`` boolean on BGP peers and peer groups with a foreign key to
``BFDProfile``.

The data migration preserves intent: any row with ``bfd=True`` is pointed at a
single shared profile named ``default`` (created on demand, all intervals null,
meaning platform defaults), so a session that rendered "BFD on" before the
migration still does afterwards. Rows with ``bfd=False`` become null.
"""

import django.db.models.deletion
from django.db import migrations, models


def bfd_boolean_to_profile(apps, schema_editor):
    BFDProfile = apps.get_model('netbox_routing_protocols', 'BFDProfile')

    for model_name in ('BGPPeer', 'BGPPeergroup'):
        model = apps.get_model('netbox_routing_protocols', model_name)
        enabled = model.objects.filter(bfd_old=True)
        if enabled.exists():
            profile, _ = BFDProfile.objects.get_or_create(name='default', device=None)
            enabled.update(bfd=profile)


def bfd_profile_to_boolean(apps, schema_editor):
    for model_name in ('BGPPeer', 'BGPPeergroup'):
        model = apps.get_model('netbox_routing_protocols', model_name)
        model.objects.filter(bfd__isnull=False).update(bfd_old=True)
        model.objects.filter(bfd__isnull=True).update(bfd_old=False)


class Migration(migrations.Migration):
    dependencies = [
        ('netbox_routing_protocols', '0004_bfdprofile'),
    ]

    operations = [
        migrations.RenameField(
            model_name='bgppeer',
            old_name='bfd',
            new_name='bfd_old',
        ),
        migrations.RenameField(
            model_name='bgppeergroup',
            old_name='bfd',
            new_name='bfd_old',
        ),
        migrations.AddField(
            model_name='bgppeer',
            name='bfd',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='%(class)ss',
                to='netbox_routing_protocols.bfdprofile',
            ),
        ),
        migrations.AddField(
            model_name='bgppeergroup',
            name='bfd',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='%(class)ss',
                to='netbox_routing_protocols.bfdprofile',
            ),
        ),
        migrations.RunPython(bfd_boolean_to_profile, bfd_profile_to_boolean),
        migrations.RemoveField(
            model_name='bgppeer',
            name='bfd_old',
        ),
        migrations.RemoveField(
            model_name='bgppeergroup',
            name='bfd_old',
        ),
    ]
