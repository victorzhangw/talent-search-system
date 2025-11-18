from collections import defaultdict

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


CREATE_TABLE_IF_NEEDED_SQL = """
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_schema = current_schema()
          AND table_name = 'test_project_trait'
    ) THEN
        IF NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = 'test_project_trait'
              AND column_name = 'trait_id'
        ) OR NOT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_schema = current_schema()
              AND table_name = 'test_project_trait'
              AND column_name = 'test_project_id'
        ) THEN
            DROP TABLE test_project_trait CASCADE;
        ELSE
            RETURN;
        END IF;
    END IF;

    CREATE TABLE test_project_trait (
        id BIGSERIAL PRIMARY KEY,
        custom_description TEXT NOT NULL DEFAULT '',
        use_custom_description BOOLEAN NOT NULL DEFAULT FALSE,
        sort_order INTEGER NOT NULL DEFAULT 0,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        test_project_id BIGINT NOT NULL REFERENCES test_project (id) ON DELETE CASCADE,
        trait_id BIGINT NOT NULL REFERENCES trait (id) ON DELETE RESTRICT,
        UNIQUE (test_project_id, trait_id)
    );
END;
$$;
"""


DROP_TABLE_SQL = "DROP TABLE IF EXISTS test_project_trait CASCADE;"


def populate_test_project_traits(apps, schema_editor):
    TestProjectTrait = apps.get_model('core', 'TestProjectTrait')
    CategoryTrait = apps.get_model('core', 'TestProjectCategoryTrait')

    existing_keys = set(
        TestProjectTrait.objects.values_list('test_project_id', 'trait_id')
    )
    project_next_sort = defaultdict(int)
    for project_id, sort_order in TestProjectTrait.objects.values_list(
        'test_project_id', 'sort_order'
    ):
        project_next_sort[project_id] = max(project_next_sort[project_id], sort_order + 1)

    seen = set()
    new_records = []

    category_traits_qs = CategoryTrait.objects.select_related('category').order_by(
        'category__test_project_id', 'trait_id', 'id'
    )

    for category_trait in category_traits_qs.iterator():
        project_id = category_trait.category.test_project_id if category_trait.category else None
        trait_id = category_trait.trait_id

        if not project_id or not trait_id:
            continue

        key = (project_id, trait_id)
        if key in existing_keys or key in seen:
            continue

        sort_order = project_next_sort[project_id]
        project_next_sort[project_id] = sort_order + 1

        new_records.append(
            TestProjectTrait(
                test_project_id=project_id,
                trait_id=trait_id,
                custom_description='',
                use_custom_description=False,
                sort_order=sort_order,
            )
        )
        seen.add(key)

    if new_records:
        TestProjectTrait.objects.bulk_create(new_records)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_enterprise_purchase_record'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name='TestProjectTrait',
                    fields=[
                        ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                        ('custom_description', models.TextField(blank=True, verbose_name='特質自訂描述')),
                        ('use_custom_description', models.BooleanField(default=False, verbose_name='是否使用自訂描述')),
                        ('sort_order', models.IntegerField(default=0, verbose_name='排序')),
                        ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='建立時間')),
                        ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新時間')),
                        ('test_project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='project_trait_relations', to='core.testproject', verbose_name='測驗項目')),
                        ('trait', models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name='test_project_trait_relations', to='core.trait', verbose_name='特質')),
                    ],
                    options={
                        'verbose_name': '測驗項目特質',
                        'verbose_name_plural': '測驗項目特質',
                        'db_table': 'test_project_trait',
                        'ordering': ['test_project', 'sort_order', 'id'],
                        'unique_together': {('test_project', 'trait')},
                    },
                ),
            ],
            database_operations=[
                migrations.RunSQL(
                    sql=CREATE_TABLE_IF_NEEDED_SQL,
                    reverse_sql=DROP_TABLE_SQL,
                )
            ],
        ),
        migrations.AddField(
            model_name='testproject',
            name='traits',
            field=models.ManyToManyField(blank=True, related_name='test_projects', through='core.TestProjectTrait', to='core.trait', verbose_name='測驗特質'),
        ),
        migrations.RunPython(populate_test_project_traits, migrations.RunPython.noop),
    ]
