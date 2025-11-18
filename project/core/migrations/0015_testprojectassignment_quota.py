from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_alter_user_email'),
    ]

    operations = [
        migrations.AddField(
            model_name='testprojectassignment',
            name='assigned_quota',
            field=models.PositiveIntegerField(default=0, help_text='0 表示不限', verbose_name='可用份數'),
        ),
        migrations.AddField(
            model_name='testprojectassignment',
            name='used_quota',
            field=models.PositiveIntegerField(default=0, verbose_name='已使用份數'),
        ),
    ]
