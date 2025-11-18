from decimal import Decimal

from django.db import migrations, models
from django.utils import timezone


def migrate_traits_forward(apps, schema_editor):
    TestProjectTrait = apps.get_model('core', 'TestProjectTrait')
    Trait = apps.get_model('core', 'Trait')
    CategoryTrait = apps.get_model('core', 'TestProjectCategoryTrait')

    processed_system_names = set()

    for old_trait in TestProjectTrait.objects.select_related('category').order_by('id'):
        if not old_trait.category_id:
            continue

        system_name = (old_trait.system_name or '').strip()
        if not system_name:
            continue

        defaults = {
            'chinese_name': old_trait.chinese_name or system_name,
            'description': old_trait.description or '',
        }
        trait_obj, created = Trait.objects.get_or_create(
            system_name=system_name,
            defaults=defaults
        )

        if not created:
            update_fields = []
            if old_trait.chinese_name and trait_obj.chinese_name != old_trait.chinese_name:
                trait_obj.chinese_name = old_trait.chinese_name
                update_fields.append('chinese_name')
            if old_trait.description and trait_obj.description != old_trait.description:
                trait_obj.description = old_trait.description
                update_fields.append('description')
            if update_fields:
                trait_obj.save(update_fields=update_fields)

        CategoryTrait.objects.get_or_create(
            category=old_trait.category,
            trait=trait_obj,
            defaults={
                'weight': Decimal('1.00'),
                'sort_order': old_trait.sort_order,
            }
        )


def migrate_traits_backward(apps, schema_editor):
    TestProjectTrait = apps.get_model('core', 'TestProjectTrait')
    Trait = apps.get_model('core', 'Trait')
    CategoryTrait = apps.get_model('core', 'TestProjectCategoryTrait')

    TestProjectTrait.objects.all().delete()

    for category_trait in CategoryTrait.objects.select_related('category', 'trait').order_by('id'):
        trait = category_trait.trait
        TestProjectTrait.objects.create(
            category=category_trait.category,
            chinese_name=trait.chinese_name,
            system_name=trait.system_name,
            description=trait.description,
            sort_order=category_trait.sort_order,
        )


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0015_testprojectassignment_quota'),
    ]

    operations = [
        migrations.CreateModel(
            name='Trait',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('chinese_name', models.CharField(max_length=100, verbose_name='中文特質名稱')),
                ('system_name', models.CharField(max_length=100, unique=True, verbose_name='系統對應名稱')),
                ('description', models.TextField(blank=True, verbose_name='特質描述')),
                ('created_at', models.DateTimeField(default=timezone.now, verbose_name='建立時間')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新時間')),
            ],
            options={
                'verbose_name': '特質',
                'verbose_name_plural': '特質',
                'db_table': 'trait',
                'ordering': ['system_name'],
            },
        ),
        migrations.CreateModel(
            name='TestProjectCategoryTrait',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('weight', models.DecimalField(decimal_places=2, default=Decimal('1.00'), max_digits=6, verbose_name='權重')),
                ('sort_order', models.IntegerField(default=0, verbose_name='排序')),
                ('created_at', models.DateTimeField(default=timezone.now, verbose_name='建立時間')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新時間')),
                ('category', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='category_traits', to='core.testprojectcategory', verbose_name='測驗分類')),
                ('trait', models.ForeignKey(on_delete=models.deletion.PROTECT, related_name='category_traits', to='core.trait', verbose_name='特質')),
            ],
            options={
                'verbose_name': '分類特質',
                'verbose_name_plural': '分類特質',
                'db_table': 'test_project_category_trait',
                'ordering': ['category', 'sort_order', 'id'],
            },
        ),
        migrations.AddField(
            model_name='testprojectcategory',
            name='traits',
            field=models.ManyToManyField(blank=True, related_name='categories', through='core.TestProjectCategoryTrait', to='core.trait', verbose_name='特質'),
        ),
        migrations.AlterUniqueTogether(
            name='testprojectcategorytrait',
            unique_together={('category', 'trait')},
        ),
        migrations.RunPython(migrate_traits_forward, migrate_traits_backward),
    ]
