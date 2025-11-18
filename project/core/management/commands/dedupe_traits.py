from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count
from django.apps import apps


class Command(BaseCommand):
    help = '移除 Trait 表中重複的 system_name，保留最早建立的一筆並更新引用資料'

    def handle(self, *args, **options):
        Trait = apps.get_model('core', 'Trait')
        TestProjectCategoryTrait = apps.get_model('core', 'TestProjectCategoryTrait')
        try:
            TestProjectTrait = apps.get_model('core', 'TestProjectTrait')
        except LookupError:
            TestProjectTrait = None

        duplicates = (
            Trait.objects.values('system_name')
            .annotate(total=Count('id'))
            .filter(total__gt=1)
        )

        using_trait_table = duplicates.exists()

        if not using_trait_table:
            if TestProjectTrait is None or not TestProjectTrait.objects.exists():
                self.stdout.write(self.style.SUCCESS('沒有發現重複的 Trait 資料'))
                return

            duplicates = (
                TestProjectTrait.objects.values('system_name')
                .annotate(total=Count('id'))
                .filter(total__gt=1)
            )
            if not duplicates.exists():
                self.stdout.write(self.style.SUCCESS('沒有發現重複的 Trait 資料'))
                return
            using_trait_table = False

        with transaction.atomic():
            if using_trait_table and duplicates.exists():
                for entry in duplicates:
                    system_name = entry['system_name']
                    traits = list(Trait.objects.filter(system_name=system_name).order_by('id'))
                    keeper = traits[0]
                    duplicates_to_remove = traits[1:]

                    self.stdout.write(
                        f'處理特質 {system_name}，保留 ID {keeper.id}，移除 {len(duplicates_to_remove)} 筆重複資料'
                    )

                    TestProjectCategoryTrait.objects.filter(trait__in=duplicates_to_remove).update(trait=keeper)
                    Trait.objects.filter(id__in=[t.id for t in duplicates_to_remove]).delete()

                self.stdout.write(self.style.SUCCESS('Trait 資料重複清理完成'))
            elif not using_trait_table and duplicates.exists():
                for entry in duplicates:
                    system_name = entry['system_name']
                    traits = list(TestProjectTrait.objects.filter(system_name=system_name).order_by('id'))
                    keeper = traits[0]
                    duplicates_to_remove = traits[1:]

                    self.stdout.write(
                        f'處理舊特質 {system_name}，保留 ID {keeper.id}，移除 {len(duplicates_to_remove)} 筆重複資料'
                    )

                    TestProjectTrait.objects.filter(id__in=[t.id for t in duplicates_to_remove]).delete()

                self.stdout.write(self.style.SUCCESS('舊 TestProjectTrait 資料重複清理完成'))
            else:
                self.stdout.write(self.style.SUCCESS('沒有發現重複的 Trait 資料'))
