from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ticket', '0001_initial'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='checkinlog',
            index=models.Index(fields=['guest', 'status'], name='chklog_gst_st_idx'),
        ),
    ]
