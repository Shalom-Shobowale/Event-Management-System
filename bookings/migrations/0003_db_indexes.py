from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bookings', '0002_initial'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='booking',
            index=models.Index(fields=['vendor', 'status'], name='booking_ven_st_idx'),
        ),
        migrations.AddIndex(
            model_name='booking',
            index=models.Index(fields=['event', 'status'], name='booking_evt_st_idx'),
        ),
        migrations.AddIndex(
            model_name='quoterequest',
            index=models.Index(fields=['status', 'is_urgent'], name='rfq_st_urg_idx'),
        ),
        migrations.AddIndex(
            model_name='proposal',
            index=models.Index(fields=['vendor', 'status'], name='prop_ven_st_idx'),
        ),
    ]
