
<template>
  <div class="user-management">
    <div class="header-section">
      <h2>使用者管理</h2>
      <BaseButton @click="showAddUserModal = true">
        <Plus :size="16" /> 新增使用者
      </BaseButton>
    </div>

    <BaseCard>
      <div v-if="loading" class="loading">載入中...</div>
      <div v-else-if="error" class="error">{{ error }}</div>
      <table v-else class="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>使用者名稱</th>
            <th>建立時間</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.id">
            <td>#{{ user.id }}</td>
            <td>{{ user.username }}</td>
            <td>{{ formatDate(user.created_at) }}</td>
            <td>
              <BaseButton variant="secondary" size="sm" @click="openPasswordModal(user)">
                重設密碼
              </BaseButton>
            </td>
          </tr>
        </tbody>
      </table>
    </BaseCard>

    <!-- Generic Modal for Add User -->
    <div v-if="showAddUserModal" class="modal-overlay">
      <div class="modal-content">
        <h3>新增使用者</h3>
        <form @submit.prevent="createUser">
          <BaseInput v-model="newUser.username" label="使用者名稱" required />
          <BaseInput v-model="newUser.password" label="密碼" type="password" required />
          <div class="modal-actions">
             <BaseButton type="button" variant="secondary" @click="showAddUserModal = false">取消</BaseButton>
             <BaseButton type="submit" :loading="actionLoading">建立</BaseButton>
          </div>
        </form>
      </div>
    </div>

    <!-- Password Modal -->
    <div v-if="showPasswordModal" class="modal-overlay">
      <div class="modal-content">
        <h3>重設密碼: {{ selectedUser?.username }}</h3>
        <form @submit.prevent="updatePassword">
          <BaseInput v-model="newPassword" label="新密碼" type="password" required />
          <div class="modal-actions">
             <BaseButton type="button" variant="secondary" @click="showPasswordModal = false">取消</BaseButton>
             <BaseButton type="submit" :loading="actionLoading">更新</BaseButton>
          </div>
        </form>
      </div>
    </div>

  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import BaseCard from '@/components/base/BaseCard.vue'
import BaseButton from '@/components/base/BaseButton.vue'
import BaseInput from '@/components/base/BaseInput.vue'
import { Plus } from 'lucide-vue-next'
import { useAuthStore } from '@/stores/auth'

const users = ref([])
const loading = ref(false)
const error = ref('')
const actionLoading = ref(false)

const showAddUserModal = ref(false)
const newUser = ref({ username: '', password: '' })

const showPasswordModal = ref(false)
const selectedUser = ref(null)
const newPassword = ref('')

const authStore = useAuthStore()

const fetchUsers = async () => {
    loading.value = true
    try {
        const res = await axios.get('/api/admin/users', {
            headers: { Authorization: `Bearer ${authStore.token}` }
        })
        users.value = res.data
    } catch (e) {
        error.value = "無法載入使用者列表"
        console.error(e)
    } finally {
        loading.value = false
    }
}

const createUser = async () => {
    actionLoading.value = true
    try {
        await axios.post('/api/admin/users', newUser.value, {
            headers: { Authorization: `Bearer ${authStore.token}` }
        })
        showAddUserModal.value = false
        newUser.value = { username: '', password: '' }
        fetchUsers() // Refresh
    } catch (e) {
        alert(e.response?.data?.detail || "建立失敗")
    } finally {
        actionLoading.value = false
    }
}

const openPasswordModal = (user) => {
    selectedUser.value = user
    showPasswordModal.value = true
    newPassword.value = ''
}

const updatePassword = async () => {
    if (!selectedUser.value) return
    actionLoading.value = true
    try {
        await axios.put(`/api/admin/users/${selectedUser.value.id}/password`, {
            password: newPassword.value
        }, {
             headers: { Authorization: `Bearer ${authStore.token}` }
        })
        showPasswordModal.value = false
        alert("密碼更新成功")
    } catch (e) {
        alert("更新失敗")
    } finally {
        actionLoading.value = false
    }
}

const formatDate = (str) => {
    if (!str) return '-'
    return new Date(str).toLocaleString('zh-TW')
}

onMounted(fetchUsers)
</script>

<style lang="scss" scoped>
.user-management {
    .header-section {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1.5rem;
        h2 { margin: 0; font-size: 1.25rem; }
    }
}

.data-table {
    width: 100%;
    border-collapse: collapse;
    
    th, td {
        padding: 1rem;
        text-align: left;
        border-bottom: 1px solid $border-color;
    }
    th {
        font-weight: 600;
        color: $text-muted;
        background: $bg-body;
    }
}

.modal-overlay {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: rgba(0,0,0,0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
}

.modal-content {
    background: white;
    padding: 2rem;
    border-radius: $border-radius;
    width: 400px;
    box-shadow: $shadow-lg;
    
    h3 { margin-top: 0; margin-bottom: 1.5rem; }
    
    .modal-actions {
        display: flex;
        justify-content: flex-end;
        gap: 1rem;
        margin-top: 1.5rem;
    }
}
</style>
