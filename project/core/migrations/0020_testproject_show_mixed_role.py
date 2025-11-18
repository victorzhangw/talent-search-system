from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0019_testproject_radar_mode"),
    ]

    operations = [
        migrations.AddField(
            model_name="testproject",
            name="show_mixed_role",
            field=models.BooleanField(default=True, verbose_name="顯示混合型角色"),
        ),
    ]
