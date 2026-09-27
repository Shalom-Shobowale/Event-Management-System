from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('admin_panel', '0001_initial'),
    ]

    operations = [
        migrations.AddIndex(
            model_name='supportticket',
            index=models.Index(fields=['status', 'priority'], name='tkt_st_pri_idx'),
        ),
        migrations.AddIndex(
            model_name='report',
            index=models.Index(fields=['status', 'priority'], name='rpt_st_pri_idx'),
        ),
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(fields=['action', 'created_at'], name='audit_act_dt_idx'),
        ),
        migrations.AddIndex(
            model_name='securityevent',
            index=models.Index(fields=['is_resolved', 'severity'], name='secev_res_sev_idx'),
        ),
    ]
