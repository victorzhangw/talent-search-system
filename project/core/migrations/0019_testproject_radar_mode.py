from django.db import migrations, models

class Migration(migrations.Migration):

    dependencies = [
        ("core", "0018_testprojecttrait"),
    ]

    operations = [
        migrations.AddField(
            model_name="testproject",
            name="radar_mode",
            field=models.CharField(
                choices=[("role", "Role-based"), ("score", "Score-based")],
                default="role",
                max_length=10,
                verbose_name="雷達圖模式",
            ),
        ),
    ]
