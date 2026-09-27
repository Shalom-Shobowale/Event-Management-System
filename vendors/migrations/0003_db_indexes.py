from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('vendors', '0002_vendor_admin_notes_vendor_badge_vendor_is_suspended_and_more'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='vendor',
            index=models.Index(fields=['is_active', 'is_suspended'], name='vendor_act_susp_idx'),
        ),
        migrations.AddIndex(
            model_name='vendor',
            index=models.Index(fields=['verification_status'], name='vendor_verif_idx'),
        ),
        migrations.AddIndex(
            model_name='vendor',
            index=models.Index(fields=['city'], name='vendor_city_idx'),
        ),
    ]
