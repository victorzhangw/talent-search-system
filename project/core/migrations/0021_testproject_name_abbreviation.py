from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0020_testproject_show_mixed_role'),
    ]

    operations = [
        migrations.AddField(
            model_name='testproject',
            name='name_abbreviation',
            field=models.CharField(
                blank=True,
                default='',
                help_text='僅供下載檔名使用',
                max_length=50,
                verbose_name='測驗名稱縮寫',
            ),
            preserve_default=False,
        ),
    ]
