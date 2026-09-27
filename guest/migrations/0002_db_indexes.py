from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('guest', '0001_initial'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='guest',
            index=models.Index(fields=['event', 'checked_in'], name='guest_event_chk_idx'),
        ),
        migrations.AddIndex(
            model_name='guest',
            index=models.Index(fields=['ticket_code'], name='guest_ticket_idx'),
        ),
    ]
