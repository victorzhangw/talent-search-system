from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_trait_normalization'),
    ]

    operations = [
        migrations.CreateModel(
            name='EnterprisePurchaseRecord',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order_number', models.CharField(max_length=50, unique=True, verbose_name='訂單編號')),
                ('quantity', models.PositiveIntegerField(verbose_name='購買份數')),
                ('payment_date', models.DateTimeField(verbose_name='付款日期')),
                ('payment_method', models.CharField(blank=True, choices=[('credit_card', '信用卡'), ('atm', 'ATM')], max_length=20, verbose_name='付款方式')),
                ('payment_amount', models.DecimalField(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name='付款金額')),
                ('invoice_number', models.CharField(blank=True, max_length=50, verbose_name='發票號碼')),
                ('invoice_random_code', models.CharField(blank=True, max_length=10, verbose_name='發票隨機碼')),
                ('invoice_info', models.TextField(blank=True, verbose_name='發票資訊')),
                ('coupon_code', models.CharField(blank=True, max_length=50, verbose_name='優惠券')),
                ('notes', models.TextField(blank=True, verbose_name='備註')),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='建立時間')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新時間')),
                ('assignment', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='purchase_records', to='core.testprojectassignment', verbose_name='企業指派')),
                ('created_by', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_purchase_records', to='core.user', verbose_name='建立者')),
                ('enterprise_user', models.ForeignKey(limit_choices_to={'user_type': 'enterprise'}, on_delete=django.db.models.deletion.CASCADE, related_name='purchase_records', to='core.user', verbose_name='企業用戶')),
                ('test_project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='purchase_records', to='core.testproject', verbose_name='測驗項目')),
            ],
            options={
                'verbose_name': '企業購買紀錄',
                'verbose_name_plural': '企業購買紀錄',
                'db_table': 'enterprise_purchase_record',
                'ordering': ['-payment_date', '-id'],
            },
        ),
        migrations.CreateModel(
            name='EnterpriseQuotaUsageLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(choices=[('consume', '測驗'), ('release', '取消')], max_length=20, verbose_name='操作')),
                ('quantity', models.PositiveIntegerField(default=1, verbose_name='異動份數')),
                ('invitee_name', models.CharField(blank=True, max_length=100, verbose_name='受測者姓名')),
                ('invitee_email', models.CharField(blank=True, max_length=255, verbose_name='受測者 Email')),
                ('action_time', models.DateTimeField(default=django.utils.timezone.now, verbose_name='操作時間')),
                ('remaining_quota', models.IntegerField(blank=True, null=True, verbose_name='剩餘份數')),
                ('assignment', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='quota_logs', to='core.testprojectassignment', verbose_name='企業指派')),
                ('created_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='recorded_quota_logs', to='core.user', verbose_name='紀錄建立者')),
                ('enterprise_user', models.ForeignKey(limit_choices_to={'user_type': 'enterprise'}, on_delete=django.db.models.deletion.CASCADE, related_name='quota_usage_logs', to='core.user', verbose_name='企業用戶')),
                ('invitation', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='quota_logs', to='core.testinvitation', verbose_name='邀請紀錄')),
                ('test_project', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='quota_usage_logs', to='core.testproject', verbose_name='測驗項目')),
            ],
            options={
                'verbose_name': '企業份數使用紀錄',
                'verbose_name_plural': '企業份數使用紀錄',
                'db_table': 'enterprise_quota_usage_log',
                'ordering': ['-action_time', '-id'],
            },
        ),
    ]

