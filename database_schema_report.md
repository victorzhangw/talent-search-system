# 資料庫結構分析報告
**資料庫**: projectdb
**總表數**: 43
**總關係數**: 105
**生成時間**: null

---

## 📋 表摘要

| 表名 | 記錄數 | 欄位數 | 主鍵 | 外鍵數 |
|------|--------|--------|------|--------|
| public.auth_group | 0 | 2 | id | 0 |
| public.auth_group_permissions | 0 | 3 | id | 2 |
| public.auth_permission | 156 | 4 | id | 1 |
| public.core_user | 19 | 20 | id | 0 |
| public.core_user_groups | 0 | 3 | id | 2 |
| public.core_user_user_permissions | 0 | 3 | id | 2 |
| public.crawler_config | 1 | 8 | id | 0 |
| public.crawler_detail_logs | 2,950 | 14 | id | 2 |
| public.crawler_logs | 2,061 | 10 | id | 0 |
| public.django_admin_log | 0 | 8 | id | 2 |
| public.django_celery_beat_clockedschedule | 0 | 2 | id | 0 |
| public.django_celery_beat_crontabschedule | 8 | 7 | id | 0 |
| public.django_celery_beat_intervalschedule | 0 | 3 | id | 0 |
| public.django_celery_beat_periodictask | 3 | 23 | id | 4 |
| public.django_celery_beat_periodictasks | 1 | 2 | ident | 0 |
| public.django_celery_beat_solarschedule | 0 | 4 | id | 0 |
| public.django_content_type | 39 | 3 | id | 0 |
| public.django_migrations | 57 | 4 | id | 0 |
| public.django_session | 30 | 3 | session_key | 0 |
| public.enterprise_profile | 15 | 9 | id | 1 |
| public.enterprise_purchase_record | 0 | 17 | id | 4 |
| public.enterprise_quota_usage_log | 1 | 12 | id | 5 |
| public.individual_profile | 3 | 7 | id | 1 |
| public.individual_test_record | 2 | 13 | id | 3 |
| public.individual_test_result | 1 | 24 | id | 3 |
| public.invitation_template | 0 | 12 | id | 1 |
| public.notification | 11 | 13 | id | 2 |
| public.point_order | 0 | 14 | id | 2 |
| public.point_package | 0 | 10 | id | 0 |
| public.point_transaction | 84 | 11 | id | 1 |
| public.test_category_old | 0 | 5 | id | 0 |
| public.test_invitation | 53 | 15 | id | 4 |
| public.test_invitee | 47 | 14 | id | 1 |
| public.test_project | 3 | 23 | id | 1 |
| public.test_project_assignment | 18 | 8 | id | 3 |
| public.test_project_category | 12 | 20 | id | 1 |
| public.test_project_category_trait | 79 | 7 | id | 2 |
| public.test_project_individual_assignment | 0 | 6 | id | 3 |
| public.test_project_result | 27 | 15 | id | 2 |
| public.test_project_trait | 54 | 8 | id | 2 |
| public.test_template | 0 | 9 | id | 1 |
| public.trait | 50 | 6 | id | 0 |
| public.user_point_balance | 13 | 7 | id | 1 |

---

## 🔗 表關係分析

### 顯式外鍵約束

```
public.auth_group_permissions.group_id → public.auth_group.id
public.auth_group_permissions.permission_id → public.auth_permission.id
public.auth_permission.content_type_id → public.django_content_type.id
public.core_user_groups.user_id → public.core_user.id
public.core_user_groups.group_id → public.auth_group.id
public.core_user_user_permissions.user_id → public.core_user.id
public.core_user_user_permissions.permission_id → public.auth_permission.id
public.crawler_detail_logs.crawler_log_id → public.crawler_logs.id
public.crawler_detail_logs.test_invitation_id → public.test_invitation.id
public.django_admin_log.content_type_id → public.django_content_type.id
public.django_admin_log.user_id → public.core_user.id
public.django_celery_beat_periodictask.crontab_id → public.django_celery_beat_crontabschedule.id
public.django_celery_beat_periodictask.interval_id → public.django_celery_beat_intervalschedule.id
public.django_celery_beat_periodictask.solar_id → public.django_celery_beat_solarschedule.id
public.django_celery_beat_periodictask.clocked_id → public.django_celery_beat_clockedschedule.id
public.enterprise_profile.user_id → public.core_user.id
public.enterprise_purchase_record.assignment_id → public.test_project_assignment.id
public.enterprise_purchase_record.created_by_id → public.core_user.id
public.enterprise_purchase_record.enterprise_user_id → public.core_user.id
public.enterprise_purchase_record.test_project_id → public.test_project.id
public.enterprise_quota_usage_log.assignment_id → public.test_project_assignment.id
public.enterprise_quota_usage_log.created_by_id → public.core_user.id
public.enterprise_quota_usage_log.enterprise_user_id → public.core_user.id
public.enterprise_quota_usage_log.invitation_id → public.test_invitation.id
public.enterprise_quota_usage_log.test_project_id → public.test_project.id
public.individual_profile.user_id → public.core_user.id
public.individual_test_record.point_transaction_id → public.point_transaction.id
public.individual_test_record.test_project_id → public.test_project.id
public.individual_test_record.user_id → public.core_user.id
public.individual_test_result.individual_test_record_id → public.individual_test_record.id
public.individual_test_result.test_project_id → public.test_project.id
public.individual_test_result.user_id → public.core_user.id
public.invitation_template.enterprise_id → public.core_user.id
public.notification.content_type_id → public.django_content_type.id
public.notification.recipient_id → public.core_user.id
public.point_order.package_id → public.point_package.id
public.point_order.user_id → public.core_user.id
public.point_transaction.user_id → public.core_user.id
public.test_invitation.invitee_id → public.test_invitee.id
public.test_invitation.test_project_id → public.test_project.id
public.test_invitation.test_template_id → public.test_template.id
public.test_invitation.enterprise_id → public.core_user.id
public.test_invitee.enterprise_id → public.core_user.id
public.test_project.created_by_id → public.core_user.id
public.test_project_assignment.assigned_by_id → public.core_user.id
public.test_project_assignment.enterprise_user_id → public.core_user.id
public.test_project_assignment.test_project_id → public.test_project.id
public.test_project_category.test_project_id → public.test_project.id
public.test_project_category_trait.category_id → public.test_project_category.id
public.test_project_category_trait.trait_id → public.trait.id
public.test_project_individual_assignment.assigned_by_id → public.core_user.id
public.test_project_individual_assignment.individual_user_id → public.core_user.id
public.test_project_individual_assignment.test_project_id → public.test_project.id
public.test_project_result.test_invitation_id → public.test_invitation.id
public.test_project_result.test_project_id → public.test_project.id
public.test_project_trait.test_project_id → public.test_project.id
public.test_project_trait.trait_id → public.trait.id
public.test_template.category_id → public.test_category_old.id
public.user_point_balance.user_id → public.core_user.id
```

### 推斷的隱含關係

基於欄位命名模式推斷的關係：

| 來源表 | 來源欄位 | 目標表 | 目標欄位 | 信心度 |
|--------|----------|--------|----------|--------|
| public.core_user_groups | user_id | public.core_user | id | medium |
| public.core_user_groups | user_id | public.core_user_groups | id | medium |
| public.core_user_groups | user_id | public.core_user_user_permissions | id | medium |
| public.core_user_groups | user_id | public.user_point_balance | id | medium |
| public.core_user_user_permissions | user_id | public.core_user | id | medium |
| public.core_user_user_permissions | user_id | public.core_user_groups | id | medium |
| public.core_user_user_permissions | user_id | public.core_user_user_permissions | id | medium |
| public.core_user_user_permissions | user_id | public.user_point_balance | id | medium |
| public.django_admin_log | user_id | public.core_user | id | medium |
| public.django_admin_log | user_id | public.core_user_groups | id | medium |
| public.django_admin_log | user_id | public.core_user_user_permissions | id | medium |
| public.django_admin_log | user_id | public.user_point_balance | id | medium |
| public.enterprise_profile | user_id | public.core_user | id | medium |
| public.enterprise_profile | user_id | public.core_user_groups | id | medium |
| public.enterprise_profile | user_id | public.core_user_user_permissions | id | medium |
| public.enterprise_profile | user_id | public.user_point_balance | id | medium |
| public.individual_profile | user_id | public.core_user | id | medium |
| public.individual_profile | user_id | public.core_user_groups | id | medium |
| public.individual_profile | user_id | public.core_user_user_permissions | id | medium |
| public.individual_profile | user_id | public.user_point_balance | id | medium |
| public.individual_test_record | user_id | public.core_user | id | medium |
| public.individual_test_record | user_id | public.core_user_groups | id | medium |
| public.individual_test_record | user_id | public.core_user_user_permissions | id | medium |
| public.individual_test_record | user_id | public.user_point_balance | id | medium |
| public.individual_test_result | user_id | public.core_user | id | medium |
| public.individual_test_result | user_id | public.core_user_groups | id | medium |
| public.individual_test_result | user_id | public.core_user_user_permissions | id | medium |
| public.individual_test_result | user_id | public.user_point_balance | id | medium |
| public.point_order | user_id | public.core_user | id | medium |
| public.point_order | user_id | public.core_user_groups | id | medium |
| public.point_order | user_id | public.core_user_user_permissions | id | medium |
| public.point_order | user_id | public.user_point_balance | id | medium |
| public.point_transaction | user_id | public.core_user | id | medium |
| public.point_transaction | user_id | public.core_user_groups | id | medium |
| public.point_transaction | user_id | public.core_user_user_permissions | id | medium |
| public.point_transaction | user_id | public.user_point_balance | id | medium |
| public.test_project_category_trait | trait_id | public.test_project_category_trait | id | medium |
| public.test_project_category_trait | trait_id | public.test_project_trait | id | medium |
| public.test_project_category_trait | trait_id | public.trait | id | medium |
| public.test_project_trait | trait_id | public.test_project_category_trait | id | medium |
| public.test_project_trait | trait_id | public.test_project_trait | id | medium |
| public.test_project_trait | trait_id | public.trait | id | medium |
| public.user_point_balance | user_id | public.core_user | id | medium |
| public.user_point_balance | user_id | public.core_user_groups | id | medium |
| public.user_point_balance | user_id | public.core_user_user_permissions | id | medium |
| public.user_point_balance | user_id | public.user_point_balance | id | medium |

### 數據重複分析

⚠️ **發現以下表之間有共同欄位，可能存在數據重複**：

**public.core_user ↔ public.crawler_config**
- 共同欄位數: 3
- 共同欄位: is_active, password, username

**public.core_user ↔ public.test_invitee**
- 共同欄位數: 2
- 共同欄位: phone, email

**public.crawler_config ↔ public.invitation_template**
- 共同欄位數: 2
- 共同欄位: is_active, name

**public.crawler_config ↔ public.point_package**
- 共同欄位數: 2
- 共同欄位: is_active, name

**public.crawler_config ↔ public.test_category_old**
- 共同欄位數: 2
- 共同欄位: is_active, name

**public.crawler_config ↔ public.test_template**
- 共同欄位數: 2
- 共同欄位: is_active, name

**public.crawler_detail_logs ↔ public.crawler_logs**
- 共同欄位數: 3
- 共同欄位: error_details, status, executed_at

**public.crawler_detail_logs ↔ public.enterprise_quota_usage_log**
- 共同欄位數: 2
- 共同欄位: invitee_name, invitee_email

**public.django_admin_log ↔ public.notification**
- 共同欄位數: 2
- 共同欄位: content_type_id, object_id

**public.django_celery_beat_periodictask ↔ public.point_package**
- 共同欄位數: 2
- 共同欄位: description, name

**public.django_celery_beat_periodictask ↔ public.test_category_old**
- 共同欄位數: 2
- 共同欄位: description, name

**public.django_celery_beat_periodictask ↔ public.test_project**
- 共同欄位數: 2
- 共同欄位: description, name

**public.django_celery_beat_periodictask ↔ public.test_project_category**
- 共同欄位數: 2
- 共同欄位: description, name

**public.django_celery_beat_periodictask ↔ public.test_template**
- 共同欄位數: 2
- 共同欄位: description, name

**public.enterprise_purchase_record ↔ public.enterprise_quota_usage_log**
- 共同欄位數: 5
- 共同欄位: assignment_id, enterprise_user_id, created_by_id, test_project_id, quantity

**public.enterprise_purchase_record ↔ public.individual_test_record**
- 共同欄位數: 2
- 共同欄位: test_project_id, notes

**public.enterprise_purchase_record ↔ public.individual_test_result**
- 共同欄位數: 2
- 共同欄位: test_project_id, notes

**public.enterprise_purchase_record ↔ public.point_order**
- 共同欄位數: 3
- 共同欄位: notes, payment_method, order_number

**public.enterprise_purchase_record ↔ public.test_project_assignment**
- 共同欄位數: 2
- 共同欄位: test_project_id, enterprise_user_id

**public.enterprise_quota_usage_log ↔ public.test_project_assignment**
- 共同欄位數: 2
- 共同欄位: test_project_id, enterprise_user_id

**public.individual_test_record ↔ public.individual_test_result**
- 共同欄位數: 3
- 共同欄位: test_project_id, notes, user_id

**public.individual_test_record ↔ public.point_order**
- 共同欄位數: 3
- 共同欄位: status, notes, user_id

**public.individual_test_record ↔ public.point_transaction**
- 共同欄位數: 2
- 共同欄位: status, user_id

**public.individual_test_record ↔ public.test_invitation**
- 共同欄位數: 3
- 共同欄位: test_project_id, status, points_consumed

**public.individual_test_record ↔ public.test_invitee**
- 共同欄位數: 2
- 共同欄位: status, notes

**public.individual_test_result ↔ public.point_order**
- 共同欄位數: 2
- 共同欄位: notes, user_id

**public.individual_test_result ↔ public.test_project_result**
- 共同欄位數: 10
- 共同欄位: test_project_id, processed_data, report_generated, raw_data, crawled_at, prediction_value, category_results, trait_results, report_path, score_value

**public.invitation_template ↔ public.point_package**
- 共同欄位數: 2
- 共同欄位: is_active, name

**public.invitation_template ↔ public.test_category_old**
- 共同欄位數: 2
- 共同欄位: is_active, name

**public.invitation_template ↔ public.test_invitee**
- 共同欄位數: 2
- 共同欄位: enterprise_id, name

**public.invitation_template ↔ public.test_template**
- 共同欄位數: 2
- 共同欄位: is_active, name

**public.point_order ↔ public.point_package**
- 共同欄位數: 2
- 共同欄位: bonus_points, points

**public.point_order ↔ public.point_transaction**
- 共同欄位數: 3
- 共同欄位: status, amount, user_id

**public.point_order ↔ public.test_invitation**
- 共同欄位數: 2
- 共同欄位: status, completed_at

**public.point_order ↔ public.test_invitee**
- 共同欄位數: 2
- 共同欄位: status, notes

**public.point_package ↔ public.test_category_old**
- 共同欄位數: 3
- 共同欄位: description, is_active, name

**public.point_package ↔ public.test_project**
- 共同欄位數: 2
- 共同欄位: description, name

**public.point_package ↔ public.test_project_category**
- 共同欄位數: 3
- 共同欄位: description, name, sort_order

**public.point_package ↔ public.test_template**
- 共同欄位數: 3
- 共同欄位: description, is_active, name

**public.test_category_old ↔ public.test_project**
- 共同欄位數: 2
- 共同欄位: description, name

**public.test_category_old ↔ public.test_project_category**
- 共同欄位數: 2
- 共同欄位: description, name

**public.test_category_old ↔ public.test_template**
- 共同欄位數: 3
- 共同欄位: description, is_active, name

**public.test_invitation ↔ public.test_invitee**
- 共同欄位數: 2
- 共同欄位: status, enterprise_id

**public.test_project ↔ public.test_project_category**
- 共同欄位數: 3
- 共同欄位: description, test_link, name

**public.test_project ↔ public.test_template**
- 共同欄位數: 2
- 共同欄位: description, name

**public.test_project_assignment ↔ public.test_project_individual_assignment**
- 共同欄位數: 4
- 共同欄位: test_project_id, is_active, assigned_by_id, assigned_at

**public.test_project_category ↔ public.test_project_trait**
- 共同欄位數: 2
- 共同欄位: test_project_id, sort_order

**public.test_project_category ↔ public.test_template**
- 共同欄位數: 2
- 共同欄位: description, name

**public.test_project_category_trait ↔ public.test_project_trait**
- 共同欄位數: 2
- 共同欄位: trait_id, sort_order

🔴 **發現實際數據重複**：

**public.core_user ↔ public.test_invitee**
- 匹配欄位: phone, email
- 重複記錄數: 2

**建議**:
1. 確認這些表之間的關係
2. 考慮是否需要建立外鍵約束
3. 或者使用其中一個表作為主表，其他表引用它


---

## 📊 詳細表結構

### public.auth_group

**記錄數**: 0

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | integer | ✗ | - |
| name | character varying(150) | ✗ | - |

**索引**:

- `auth_group_name_a6ea08ec_like`: name- `auth_group_name_key` (UNIQUE): name

---

### public.auth_group_permissions

**記錄數**: 0

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | bigint | ✗ | - |
| group_id | integer | ✗ | - |
| permission_id | integer | ✗ | - |

**外鍵**:

- `group_id` → `public.auth_group.id`
- `permission_id` → `public.auth_permission.id`

**索引**:

- `auth_group_permissions_group_id_b120cbf9`: group_id- `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (UNIQUE): group_id, permission_id- `auth_group_permissions_permission_id_84c5c92e`: permission_id

---

### public.auth_permission

**記錄數**: 156

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | integer | ✗ | - |
| name | character varying(255) | ✗ | - |
| content_type_id | integer | ✗ | - |
| codename | character varying(100) | ✗ | - |

**外鍵**:

- `content_type_id` → `public.django_content_type.id`

**索引**:

- `auth_permission_content_type_id_2f476e4b`: content_type_id- `auth_permission_content_type_id_codename_01ab375a_uniq` (UNIQUE): codename, content_type_id

---

### public.core_user

**記錄數**: 19

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | bigint | ✗ | - |
| password | character varying(128) | ✗ | - |
| last_login | timestamp with time zone | ✓ | - |
| is_superuser | boolean | ✗ | - |
| username | character varying(150) | ✗ | - |
| first_name | character varying(150) | ✗ | - |
| last_name | character varying(150) | ✗ | - |
| email | character varying(254) | ✗ | - |
| is_staff | boolean | ✗ | - |
| is_active | boolean | ✗ | - |
| date_joined | timestamp with time zone | ✗ | - |
| user_type | character varying(20) | ✗ | - |
| phone | character varying(20) | ✓ | - |
| avatar | character varying(100) | ✓ | - |
| is_email_verified | boolean | ✗ | - |
| email_verification_token | uuid | ✗ | - |
| password_reset_token | uuid | ✗ | - |
| password_reset_token_created | timestamp with time zone | ✓ | - |
| created_at | timestamp with time zone | ✗ | - |
| updated_at | timestamp with time zone | ✗ | - |

**索引**:

- `core_user_email_92a71487_like`: email- `core_user_email_92a71487_uniq` (UNIQUE): email- `core_user_email_verification_token_4b35f746`: email_verification_token- `core_user_password_reset_token_f7833d47`: password_reset_token- `core_user_username_36e4f7f7_like`: username- `core_user_username_key` (UNIQUE): username

---

### public.core_user_groups

**記錄數**: 0

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | bigint | ✗ | - |
| user_id | bigint | ✗ | - |
| group_id | integer | ✗ | - |

**外鍵**:

- `user_id` → `public.core_user.id`
- `group_id` → `public.auth_group.id`

**索引**:

- `core_user_groups_group_id_fe8c697f`: group_id- `core_user_groups_user_id_70b4d9b8`: user_id- `core_user_groups_user_id_group_id_c82fcad1_uniq` (UNIQUE): group_id, user_id

---

### public.core_user_user_permissions

**記錄數**: 0

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | bigint | ✗ | - |
| user_id | bigint | ✗ | - |
| permission_id | integer | ✗ | - |

**外鍵**:

- `user_id` → `public.core_user.id`
- `permission_id` → `public.auth_permission.id`

**索引**:

- `core_user_user_permissions_permission_id_35ccf601`: permission_id- `core_user_user_permissions_user_id_085123d3`: user_id- `core_user_user_permissions_user_id_permission_id_73ea0daa_uniq` (UNIQUE): permission_id, user_id

---

### public.crawler_config

**記錄數**: 1

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | bigint | ✗ | - |
| name | character varying(100) | ✗ | - |
| base_url | character varying(200) | ✗ | - |
| username | character varying(100) | ✗ | - |
| password | character varying(100) | ✗ | - |
| is_active | boolean | ✗ | - |
| created_at | timestamp with time zone | ✗ | - |
| updated_at | timestamp with time zone | ✗ | - |

---

### public.crawler_detail_logs

**記錄數**: 2,950

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | bigint | ✗ | - |
| invitee_name | character varying(100) | ✗ | - |
| invitee_email | character varying(254) | ✗ | - |
| test_project_name | character varying(200) | ✗ | - |
| status | character varying(20) | ✗ | - |
| error_message | text | ✗ | - |
| error_details | jsonb | ✗ | - |
| attempt_count | integer | ✗ | - |
| execution_time | double precision | ✓ | - |
| data_found | boolean | ✗ | - |
| crawled_data_size | integer | ✗ | - |
| executed_at | timestamp with time zone | ✗ | - |
| crawler_log_id | bigint | ✗ | - |
| test_invitation_id | bigint | ✗ | - |

**外鍵**:

- `crawler_log_id` → `public.crawler_logs.id`
- `test_invitation_id` → `public.test_invitation.id`

**索引**:

- `crawler_detail_logs_crawler_log_id_06456694`: crawler_log_id- `crawler_detail_logs_test_invitation_id_9449058c`: test_invitation_id

---

### public.crawler_logs

**記錄數**: 2,061

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | bigint | ✗ | - |
| task_name | character varying(100) | ✗ | - |
| status | character varying(20) | ✗ | - |
| success_count | integer | ✗ | - |
| fail_count | integer | ✗ | - |
| total_count | integer | ✗ | - |
| executed_at | timestamp with time zone | ✗ | - |
| duration | interval | ✓ | - |
| message | text | ✗ | - |
| error_details | text | ✗ | - |

---

### public.django_admin_log

**記錄數**: 0

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | integer | ✗ | - |
| action_time | timestamp with time zone | ✗ | - |
| object_id | text | ✓ | - |
| object_repr | character varying(200) | ✗ | - |
| action_flag | smallint | ✗ | - |
| change_message | text | ✗ | - |
| content_type_id | integer | ✓ | - |
| user_id | bigint | ✗ | - |

**外鍵**:

- `content_type_id` → `public.django_content_type.id`
- `user_id` → `public.core_user.id`

**索引**:

- `django_admin_log_content_type_id_c4bce8eb`: content_type_id- `django_admin_log_user_id_c564eba6`: user_id

---

### public.django_celery_beat_clockedschedule

**記錄數**: 0

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | integer | ✗ | - |
| clocked_time | timestamp with time zone | ✗ | - |

---

### public.django_celery_beat_crontabschedule

**記錄數**: 8

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | integer | ✗ | - |
| minute | character varying(240) | ✗ | - |
| hour | character varying(96) | ✗ | - |
| day_of_week | character varying(64) | ✗ | - |
| day_of_month | character varying(124) | ✗ | - |
| month_of_year | character varying(64) | ✗ | - |
| timezone | character varying(63) | ✗ | - |

---

### public.django_celery_beat_intervalschedule

**記錄數**: 0

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | integer | ✗ | - |
| every | integer | ✗ | - |
| period | character varying(24) | ✗ | - |

---

### public.django_celery_beat_periodictask

**記錄數**: 3

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | integer | ✗ | - |
| name | character varying(200) | ✗ | - |
| task | character varying(200) | ✗ | - |
| args | text | ✗ | - |
| kwargs | text | ✗ | - |
| queue | character varying(200) | ✓ | - |
| exchange | character varying(200) | ✓ | - |
| routing_key | character varying(200) | ✓ | - |
| expires | timestamp with time zone | ✓ | - |
| enabled | boolean | ✗ | - |
| last_run_at | timestamp with time zone | ✓ | - |
| total_run_count | integer | ✗ | - |
| date_changed | timestamp with time zone | ✗ | - |
| description | text | ✗ | - |
| crontab_id | integer | ✓ | - |
| interval_id | integer | ✓ | - |
| solar_id | integer | ✓ | - |
| one_off | boolean | ✗ | - |
| start_time | timestamp with time zone | ✓ | - |
| priority | integer | ✓ | - |
| headers | text | ✗ | - |
| clocked_id | integer | ✓ | - |
| expire_seconds | integer | ✓ | - |

**外鍵**:

- `crontab_id` → `public.django_celery_beat_crontabschedule.id`
- `interval_id` → `public.django_celery_beat_intervalschedule.id`
- `solar_id` → `public.django_celery_beat_solarschedule.id`
- `clocked_id` → `public.django_celery_beat_clockedschedule.id`

**索引**:

- `django_celery_beat_periodictask_clocked_id_47a69f82`: clocked_id- `django_celery_beat_periodictask_crontab_id_d3cba168`: crontab_id- `django_celery_beat_periodictask_interval_id_a8ca27da`: interval_id- `django_celery_beat_periodictask_name_265a36b7_like`: name- `django_celery_beat_periodictask_name_key` (UNIQUE): name- `django_celery_beat_periodictask_solar_id_a87ce72c`: solar_id

---

### public.django_celery_beat_periodictasks

**記錄數**: 1

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **ident** 🔑 | smallint | ✗ | - |
| last_update | timestamp with time zone | ✗ | - |

---

### public.django_celery_beat_solarschedule

**記錄數**: 0

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | integer | ✗ | - |
| event | character varying(24) | ✗ | - |
| latitude | numeric | ✗ | - |
| longitude | numeric | ✗ | - |

**索引**:

- `django_celery_beat_solar_event_latitude_longitude_ba64999a_uniq` (UNIQUE): event, latitude, longitude

---

### public.django_content_type

**記錄數**: 39

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | integer | ✗ | - |
| app_label | character varying(100) | ✗ | - |
| model | character varying(100) | ✗ | - |

**索引**:

- `django_content_type_app_label_model_76bd3d3b_uniq` (UNIQUE): app_label, model

---

### public.django_migrations

**記錄數**: 57

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | bigint | ✗ | - |
| app | character varying(255) | ✗ | - |
| name | character varying(255) | ✗ | - |
| applied | timestamp with time zone | ✗ | - |

---

### public.django_session

**記錄數**: 30

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **session_key** 🔑 | character varying(40) | ✗ | - |
| session_data | text | ✗ | - |
| expire_date | timestamp with time zone | ✗ | - |

**索引**:

- `django_session_expire_date_a5c62663`: expire_date- `django_session_session_key_c0390e0f_like`: session_key

---

### public.enterprise_profile

**記錄數**: 15

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | bigint | ✗ | - |
| company_name | character varying(100) | ✗ | - |
| tax_id | character varying(8) | ✗ | - |
| contact_person | character varying(50) | ✗ | - |
| contact_phone | character varying(20) | ✗ | - |
| address | text | ✓ | - |
| verification_status | character varying(20) | ✗ | - |
| verified_at | timestamp with time zone | ✓ | - |
| user_id | bigint | ✗ | - |

**外鍵**:

- `user_id` → `public.core_user.id`

**索引**:

- `enterprise_profile_tax_id_3372305a`: tax_id- `enterprise_profile_tax_id_3372305a_like`: tax_id- `enterprise_profile_user_id_key` (UNIQUE): user_id- `unique_enterprise_user_tax_id` (UNIQUE): tax_id, user_id

---

### public.enterprise_purchase_record

**記錄數**: 0

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | integer | ✗ | - |
| order_number | character varying(50) | ✗ | - |
| quantity | integer | ✗ | - |
| payment_date | timestamp with time zone | ✗ | - |
| payment_method | character varying(20) | ✗ | - |
| payment_amount | numeric | ✓ | - |
| invoice_number | character varying(50) | ✗ | - |
| invoice_random_code | character varying(10) | ✗ | - |
| invoice_info | text | ✗ | - |
| coupon_code | character varying(50) | ✗ | - |
| notes | text | ✗ | - |
| created_at | timestamp with time zone | ✗ | - |
| updated_at | timestamp with time zone | ✗ | - |
| assignment_id | bigint | ✓ | - |
| created_by_id | bigint | ✓ | - |
| enterprise_user_id | bigint | ✗ | - |
| test_project_id | bigint | ✗ | - |

**外鍵**:

- `assignment_id` → `public.test_project_assignment.id`
- `created_by_id` → `public.core_user.id`
- `enterprise_user_id` → `public.core_user.id`
- `test_project_id` → `public.test_project.id`

**索引**:

- `enterprise_purchase_record_assignment_id_54053538`: assignment_id- `enterprise_purchase_record_created_by_id_0b995bec`: created_by_id- `enterprise_purchase_record_enterprise_user_id_a017ea1a`: enterprise_user_id- `enterprise_purchase_record_order_number_0dfcbf9a_like`: order_number- `enterprise_purchase_record_order_number_key` (UNIQUE): order_number- `enterprise_purchase_record_test_project_id_e02ae2b9`: test_project_id

---

### public.enterprise_quota_usage_log

**記錄數**: 1

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | integer | ✗ | - |
| action | character varying(20) | ✗ | - |
| quantity | integer | ✗ | - |
| invitee_name | character varying(100) | ✗ | - |
| invitee_email | character varying(255) | ✗ | - |
| action_time | timestamp with time zone | ✗ | - |
| remaining_quota | integer | ✓ | - |
| assignment_id | bigint | ✗ | - |
| created_by_id | bigint | ✓ | - |
| enterprise_user_id | bigint | ✗ | - |
| invitation_id | bigint | ✓ | - |
| test_project_id | bigint | ✗ | - |

**外鍵**:

- `assignment_id` → `public.test_project_assignment.id`
- `created_by_id` → `public.core_user.id`
- `enterprise_user_id` → `public.core_user.id`
- `invitation_id` → `public.test_invitation.id`
- `test_project_id` → `public.test_project.id`

**索引**:

- `enterprise_quota_usage_log_assignment_id_d2f25e10`: assignment_id- `enterprise_quota_usage_log_created_by_id_6cd06ec8`: created_by_id- `enterprise_quota_usage_log_enterprise_user_id_259ead93`: enterprise_user_id- `enterprise_quota_usage_log_invitation_id_4ef36102`: invitation_id- `enterprise_quota_usage_log_test_project_id_09f476d3`: test_project_id

---

### public.individual_profile

**記錄數**: 3

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | bigint | ✗ | - |
| real_name | character varying(50) | ✗ | - |
| id_number | character varying(20) | ✓ | - |
| birth_date | date | ✓ | - |
| user_id | bigint | ✗ | - |
| test_platform_password | character varying(255) | ✓ | - |
| test_platform_username | character varying(100) | ✓ | - |

**外鍵**:

- `user_id` → `public.core_user.id`

**索引**:

- `individual_profile_user_id_key` (UNIQUE): user_id

---

### public.individual_test_record

**記錄數**: 2

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | bigint | ✗ | - |
| purchase_date | timestamp with time zone | ✗ | - |
| first_access_date | timestamp with time zone | ✓ | - |
| last_access_date | timestamp with time zone | ✓ | - |
| access_count | integer | ✗ | - |
| status | character varying(20) | ✗ | - |
| points_consumed | integer | ✗ | - |
| notes | text | ✗ | - |
| created_at | timestamp with time zone | ✗ | - |
| updated_at | timestamp with time zone | ✗ | - |
| point_transaction_id | bigint | ✓ | - |
| test_project_id | bigint | ✗ | - |
| user_id | bigint | ✗ | - |

**外鍵**:

- `point_transaction_id` → `public.point_transaction.id`
- `test_project_id` → `public.test_project.id`
- `user_id` → `public.core_user.id`

**索引**:

- `individual_test_record_point_transaction_id_6afea9ed`: point_transaction_id- `individual_test_record_test_project_id_84c915ec`: test_project_id- `individual_test_record_user_id_c7a97b28`: user_id- `individual_test_record_user_id_test_project_id_4a328df4_uniq` (UNIQUE): test_project_id, user_id

---

### public.individual_test_result

**記錄數**: 1

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | bigint | ✗ | - |
| raw_data | jsonb | ✗ | - |
| processed_data | jsonb | ✗ | - |
| score_value | double precision | ✓ | - |
| prediction_value | text | ✗ | - |
| category_results | jsonb | ✗ | - |
| trait_results | jsonb | ✗ | - |
| test_completion_date | timestamp with time zone | ✓ | - |
| external_test_id | character varying(100) | ✗ | - |
| test_url | character varying(200) | ✗ | - |
| result_status | character varying(20) | ✗ | - |
| crawled_at | timestamp with time zone | ✓ | - |
| crawl_attempts | integer | ✗ | - |
| crawl_error_message | text | ✗ | - |
| report_generated | boolean | ✗ | - |
| report_path | character varying(500) | ✗ | - |
| report_generated_at | timestamp with time zone | ✓ | - |
| allow_sharing | boolean | ✗ | - |
| notes | text | ✗ | - |
| created_at | timestamp with time zone | ✗ | - |
| updated_at | timestamp with time zone | ✗ | - |
| individual_test_record_id | bigint | ✗ | - |
| test_project_id | bigint | ✗ | - |
| user_id | bigint | ✗ | - |

**外鍵**:

- `individual_test_record_id` → `public.individual_test_record.id`
- `test_project_id` → `public.test_project.id`
- `user_id` → `public.core_user.id`

**索引**:

- `individual__created_ed1a73_idx`: created_at- `individual__result__ed9d1f_idx`: result_status- `individual__user_id_ecb56b_idx`: test_project_id, user_id- `individual_test_result_individual_test_record_id_key` (UNIQUE): individual_test_record_id- `individual_test_result_test_project_id_7a79e6d7`: test_project_id- `individual_test_result_user_id_7ca98051`: user_id

---

### public.invitation_template

**記錄數**: 0

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | bigint | ✗ | - |
| name | character varying(100) | ✗ | - |
| template_type | character varying(20) | ✗ | - |
| subject_template | character varying(200) | ✗ | - |
| message_template | text | ✗ | - |
| is_default | boolean | ✗ | - |
| is_active | boolean | ✗ | - |
| usage_count | integer | ✗ | - |
| last_used_at | timestamp with time zone | ✓ | - |
| created_at | timestamp with time zone | ✗ | - |
| updated_at | timestamp with time zone | ✗ | - |
| enterprise_id | bigint | ✗ | - |

**外鍵**:

- `enterprise_id` → `public.core_user.id`

**索引**:

- `invitation_template_enterprise_id_dd896907`: enterprise_id- `invitation_template_enterprise_id_name_7d33e27f_uniq` (UNIQUE): enterprise_id, name

---

### public.notification

**記錄數**: 11

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | bigint | ✗ | - |
| title | character varying(200) | ✗ | - |
| message | text | ✗ | - |
| notification_type | character varying(20) | ✗ | - |
| priority | character varying(10) | ✗ | - |
| object_id | integer | ✓ | - |
| is_read | boolean | ✗ | - |
| read_at | timestamp with time zone | ✓ | - |
| created_at | timestamp with time zone | ✗ | - |
| expires_at | timestamp with time zone | ✓ | - |
| metadata | jsonb | ✗ | - |
| content_type_id | integer | ✓ | - |
| recipient_id | bigint | ✗ | - |

**外鍵**:

- `content_type_id` → `public.django_content_type.id`
- `recipient_id` → `public.core_user.id`

**索引**:

- `notificatio_created_db7ad3_idx`: created_at- `notificatio_notific_f8d066_idx`: notification_type- `notificatio_recipie_201701_idx`: is_read, recipient_id- `notification_content_type_id_3d1c06d3`: content_type_id- `notification_recipient_id_305d14d6`: recipient_id

---

### public.point_order

**記錄數**: 0

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | bigint | ✗ | - |
| order_number | character varying(50) | ✗ | - |
| points | integer | ✗ | - |
| bonus_points | integer | ✗ | - |
| amount | numeric | ✗ | - |
| status | character varying(20) | ✗ | - |
| payment_method | character varying(50) | ✗ | - |
| payment_reference | character varying(100) | ✗ | - |
| notes | text | ✗ | - |
| created_at | timestamp with time zone | ✗ | - |
| paid_at | timestamp with time zone | ✓ | - |
| completed_at | timestamp with time zone | ✓ | - |
| package_id | bigint | ✗ | - |
| user_id | bigint | ✗ | - |

**外鍵**:

- `package_id` → `public.point_package.id`
- `user_id` → `public.core_user.id`

**索引**:

- `point_order_created_3571a4_idx`: created_at- `point_order_order_n_4ac5ca_idx`: order_number- `point_order_order_number_1ea9a06c_like`: order_number- `point_order_order_number_key` (UNIQUE): order_number- `point_order_package_id_afb294bc`: package_id- `point_order_user_id_354c7d9f`: user_id- `point_order_user_id_6625e6_idx`: status, user_id

---

### public.point_package

**記錄數**: 0

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | bigint | ✗ | - |
| name | character varying(100) | ✗ | - |
| description | text | ✗ | - |
| points | integer | ✗ | - |
| price | numeric | ✗ | - |
| bonus_points | integer | ✗ | - |
| is_active | boolean | ✗ | - |
| sort_order | integer | ✗ | - |
| created_at | timestamp with time zone | ✗ | - |
| updated_at | timestamp with time zone | ✗ | - |

---

### public.point_transaction

**記錄數**: 84

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | bigint | ✗ | - |
| transaction_type | character varying(20) | ✗ | - |
| amount | integer | ✗ | - |
| balance_before | integer | ✗ | - |
| balance_after | integer | ✗ | - |
| description | text | ✗ | - |
| reference_id | character varying(100) | ✗ | - |
| status | character varying(20) | ✗ | - |
| metadata | jsonb | ✗ | - |
| created_at | timestamp with time zone | ✗ | - |
| user_id | bigint | ✗ | - |

**外鍵**:

- `user_id` → `public.core_user.id`

**索引**:

- `point_trans_created_2e5b77_idx`: created_at- `point_trans_referen_97367e_idx`: reference_id- `point_trans_user_id_88226f_idx`: transaction_type, user_id- `point_transaction_user_id_c5d28756`: user_id

---

### public.test_category_old

**記錄數**: 0

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | bigint | ✗ | - |
| name | character varying(100) | ✗ | - |
| description | text | ✗ | - |
| is_active | boolean | ✗ | - |
| created_at | timestamp with time zone | ✗ | - |

---

### public.test_invitation

**記錄數**: 53

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | bigint | ✗ | - |
| invitation_code | uuid | ✗ | - |
| custom_message | text | ✗ | - |
| invited_at | timestamp with time zone | ✗ | - |
| expires_at | timestamp with time zone | ✗ | - |
| started_at | timestamp with time zone | ✓ | - |
| completed_at | timestamp with time zone | ✓ | - |
| status | character varying(20) | ✗ | - |
| points_consumed | integer | ✗ | - |
| score | double precision | ✓ | - |
| result_data | jsonb | ✗ | - |
| enterprise_id | bigint | ✗ | - |
| invitee_id | bigint | ✗ | - |
| test_project_id | bigint | ✓ | - |
| test_template_id | bigint | ✓ | - |

**外鍵**:

- `invitee_id` → `public.test_invitee.id`
- `test_project_id` → `public.test_project.id`
- `test_template_id` → `public.test_template.id`
- `enterprise_id` → `public.core_user.id`

**索引**:

- `test_invita_enterpr_d1a31e_idx`: enterprise_id, status- `test_invita_invitat_d3f257_idx`: invitation_code- `test_invita_invitee_cf6df8_idx`: invitee_id- `test_invita_test_pr_80593f_idx`: test_project_id- `test_invitation_enterprise_id_fe7f4a54`: enterprise_id- `test_invitation_invitation_code_key` (UNIQUE): invitation_code- `test_invitation_invitee_id_40280acd`: invitee_id- `test_invitation_test_project_id_5ac0e711`: test_project_id- `test_invitation_test_template_id_d6bf1491`: test_template_id

---

### public.test_invitee

**記錄數**: 47

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | bigint | ✗ | - |
| name | character varying(50) | ✗ | - |
| email | character varying(254) | ✗ | - |
| phone | character varying(20) | ✗ | - |
| company | character varying(100) | ✗ | - |
| position | character varying(50) | ✗ | - |
| notes | text | ✗ | - |
| invited_count | integer | ✗ | - |
| completed_count | integer | ✗ | - |
| last_test_date | timestamp with time zone | ✓ | - |
| created_at | timestamp with time zone | ✗ | - |
| updated_at | timestamp with time zone | ✗ | - |
| enterprise_id | bigint | ✗ | - |
| status | character varying(20) | ✗ | - |

**外鍵**:

- `enterprise_id` → `public.core_user.id`

**索引**:

- `test_invitee_enterprise_id_d27b6c5f`: enterprise_id- `test_invitee_enterprise_id_email_9ccb8063_uniq` (UNIQUE): email, enterprise_id

---

### public.test_project

**記錄數**: 3

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | bigint | ✗ | - |
| name | character varying(200) | ✗ | - |
| description | text | ✗ | - |
| test_link | character varying(200) | ✗ | - |
| score_field_chinese | character varying(100) | ✗ | - |
| score_field_system | character varying(100) | ✗ | - |
| prediction_field_chinese | character varying(100) | ✗ | - |
| prediction_field_system | character varying(100) | ✗ | - |
| job_role_system_name | character varying(100) | ✗ | - |
| assignment_type | character varying(20) | ✗ | - |
| created_at | timestamp with time zone | ✗ | - |
| updated_at | timestamp with time zone | ✗ | - |
| created_by_id | bigint | ✗ | - |
| footer_text_content | text | ✗ | - |
| header_logo | character varying(100) | ✓ | - |
| header_text_content | text | ✗ | - |
| personal_share_footer_content | text | ✗ | - |
| personal_share_title | character varying(200) | ✗ | - |
| introduction | text | ✗ | - |
| precautions | text | ✗ | - |
| title_name | character varying(200) | ✗ | - |
| title_name_english | character varying(200) | ✗ | - |
| usage_guide | text | ✗ | - |

**外鍵**:

- `created_by_id` → `public.core_user.id`

**索引**:

- `test_project_created_by_id_a88338f9`: created_by_id

---

### public.test_project_assignment

**記錄數**: 18

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | bigint | ✗ | - |
| is_active | boolean | ✗ | - |
| assigned_at | timestamp with time zone | ✗ | - |
| assigned_by_id | bigint | ✗ | - |
| enterprise_user_id | bigint | ✗ | - |
| test_project_id | bigint | ✗ | - |
| assigned_quota | integer | ✗ | - |
| used_quota | integer | ✗ | - |

**外鍵**:

- `assigned_by_id` → `public.core_user.id`
- `enterprise_user_id` → `public.core_user.id`
- `test_project_id` → `public.test_project.id`

**索引**:

- `test_project_assignment_assigned_by_id_d0612442`: assigned_by_id- `test_project_assignment_enterprise_user_id_5eb32881`: enterprise_user_id- `test_project_assignment_test_project_id_14076089`: test_project_id- `test_project_assignment_test_project_id_enterpri_26731c9e_uniq` (UNIQUE): enterprise_user_id, test_project_id

---

### public.test_project_category

**記錄數**: 12

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | bigint | ✗ | - |
| name | character varying(200) | ✗ | - |
| test_link | character varying(200) | ✗ | - |
| advantage_analysis | text | ✗ | - |
| disadvantage_analysis | text | ✗ | - |
| sort_order | integer | ✗ | - |
| created_at | timestamp with time zone | ✗ | - |
| updated_at | timestamp with time zone | ✗ | - |
| test_project_id | bigint | ✗ | - |
| advantage_suggestions | text | ✗ | - |
| content | text | ✗ | - |
| development_direction | text | ✗ | - |
| role_image | character varying(100) | ✓ | - |
| role_name | character varying(200) | ✗ | - |
| score_type_name | character varying(100) | ✗ | - |
| tag_text | character varying(500) | ✗ | - |
| english_name | character varying(200) | ✗ | - |
| development_parameter_content | text | ✗ | - |
| development_parameter_name | character varying(200) | ✗ | - |
| description | text | ✗ | - |

**外鍵**:

- `test_project_id` → `public.test_project.id`

**索引**:

- `test_project_category_test_project_id_5ecdd4bd`: test_project_id

---

### public.test_project_category_trait

**記錄數**: 79

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | integer | ✗ | - |
| weight | numeric | ✗ | - |
| sort_order | integer | ✗ | - |
| created_at | timestamp with time zone | ✗ | - |
| updated_at | timestamp with time zone | ✗ | - |
| category_id | bigint | ✗ | - |
| trait_id | integer | ✗ | - |

**外鍵**:

- `category_id` → `public.test_project_category.id`
- `trait_id` → `public.trait.id`

**索引**:

- `test_project_category_trait_category_id_308b4425`: category_id- `test_project_category_trait_category_id_trait_id_a60431a8_uniq` (UNIQUE): category_id, trait_id- `test_project_category_trait_trait_id_25b0b36d`: trait_id

---

### public.test_project_individual_assignment

**記錄數**: 0

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | bigint | ✗ | - |
| is_active | boolean | ✗ | - |
| assigned_at | timestamp with time zone | ✗ | - |
| assigned_by_id | bigint | ✗ | - |
| individual_user_id | bigint | ✗ | - |
| test_project_id | bigint | ✗ | - |

**外鍵**:

- `assigned_by_id` → `public.core_user.id`
- `individual_user_id` → `public.core_user.id`
- `test_project_id` → `public.test_project.id`

**索引**:

- `test_project_individual__test_project_id_individu_ddb01604_uniq` (UNIQUE): individual_user_id, test_project_id- `test_project_individual_assignment_assigned_by_id_d626e2b6`: assigned_by_id- `test_project_individual_assignment_individual_user_id_b87ddf81`: individual_user_id- `test_project_individual_assignment_test_project_id_d4ab746d`: test_project_id

---

### public.test_project_result

**記錄數**: 27

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | bigint | ✗ | - |
| raw_data | jsonb | ✗ | - |
| processed_data | jsonb | ✗ | - |
| score_value | double precision | ✓ | - |
| prediction_value | text | ✗ | - |
| category_results | jsonb | ✗ | - |
| trait_results | jsonb | ✗ | - |
| crawled_at | timestamp with time zone | ✓ | - |
| crawl_status | character varying(20) | ✗ | - |
| report_generated | boolean | ✗ | - |
| report_path | character varying(500) | ✗ | - |
| created_at | timestamp with time zone | ✗ | - |
| updated_at | timestamp with time zone | ✗ | - |
| test_invitation_id | bigint | ✗ | - |
| test_project_id | bigint | ✗ | - |

**外鍵**:

- `test_invitation_id` → `public.test_invitation.id`
- `test_project_id` → `public.test_project.id`

**索引**:

- `test_project_result_test_invitation_id_key` (UNIQUE): test_invitation_id- `test_project_result_test_project_id_13e2d440`: test_project_id

---

### public.test_project_trait

**記錄數**: 54

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | bigint | ✗ | nextval('test_project_trait_id |
| custom_description | text | ✗ | ''::text |
| use_custom_description | boolean | ✗ | false |
| sort_order | integer | ✗ | 0 |
| created_at | timestamp with time zone | ✗ | now() |
| updated_at | timestamp with time zone | ✗ | now() |
| test_project_id | bigint | ✗ | - |
| trait_id | bigint | ✗ | - |

**外鍵**:

- `test_project_id` → `public.test_project.id`
- `trait_id` → `public.trait.id`

**索引**:

- `test_project_trait_test_project_id_trait_id_key` (UNIQUE): test_project_id, trait_id

---

### public.test_template

**記錄數**: 0

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | bigint | ✗ | - |
| name | character varying(200) | ✗ | - |
| description | text | ✗ | - |
| duration_minutes | integer | ✗ | - |
| question_count | integer | ✗ | - |
| point_cost | integer | ✗ | - |
| is_active | boolean | ✗ | - |
| created_at | timestamp with time zone | ✗ | - |
| category_id | bigint | ✗ | - |

**外鍵**:

- `category_id` → `public.test_category_old.id`

**索引**:

- `test_template_category_id_71616395`: category_id

---

### public.trait

**記錄數**: 50

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | integer | ✗ | - |
| chinese_name | character varying(100) | ✗ | - |
| system_name | character varying(100) | ✗ | - |
| description | text | ✗ | - |
| created_at | timestamp with time zone | ✗ | - |
| updated_at | timestamp with time zone | ✗ | - |

**索引**:

- `trait_system_name_8bdfa2d4_like`: system_name- `trait_system_name_key` (UNIQUE): system_name

---

### public.user_point_balance

**記錄數**: 13

**欄位**:

| 欄位名 | 類型 | 可空 | 預設值 |
|--------|------|------|--------|
| **id** 🔑 | bigint | ✗ | - |
| balance | integer | ✗ | - |
| total_earned | integer | ✗ | - |
| total_consumed | integer | ✗ | - |
| created_at | timestamp with time zone | ✗ | - |
| updated_at | timestamp with time zone | ✗ | - |
| user_id | bigint | ✗ | - |

**外鍵**:

- `user_id` → `public.core_user.id`

**索引**:

- `user_point_balance_user_id_key` (UNIQUE): user_id

---

