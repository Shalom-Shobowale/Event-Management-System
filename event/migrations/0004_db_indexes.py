from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('event', '0003_event_admin_flags_event_is_archived_and_more'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='event',
            index=models.Index(fields=['host', 'is_published'], name='event_host_pub_idx'),
        ),
        migrations.AddIndex(
            model_name='event',
            index=models.Index(fields=['date'], name='event_date_idx'),
        ),
        migrations.AddIndex(
            model_name='event',
            index=models.Index(fields=['is_suspended'], name='event_susp_idx'),
        ),
    ]
