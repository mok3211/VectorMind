<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue'
import {
  NButton,
  NCard,
  NDataTable,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NModal,
  NSelect,
  NSwitch,
  NTabPane,
  NTabs,
  NTag,
  useMessage
} from 'naive-ui'
import { api } from '@/lib/api'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const message = useMessage()

const tab = ref<'users' | 'roles' | 'plans' | 'menus'>('users')

const permissions = ref<any[]>([])
const roles = ref<any[]>([])
const users = ref<any[]>([])
const plans = ref<any[]>([])
const menus = ref<any[]>([])

const loading = ref(false)

const canUsers = computed(() => auth.hasPerm('system.users.manage'))
const canRoles = computed(() => auth.hasPerm('system.roles.manage'))
const canPerms = computed(() => auth.hasPerm('system.permissions.manage'))
const canMenus = computed(() => auth.hasPerm('system.menus.manage'))
const canPlans = computed(() => auth.hasPerm('billing.plans.manage'))

async function reloadAll() {
  loading.value = true
  try {
    if (canPerms.value) {
      permissions.value = (await api.get('/api/rbac/permissions')).data.items
    }
    if (canRoles.value) {
      roles.value = (await api.get('/api/rbac/roles')).data.items
    }
    if (canUsers.value) {
      users.value = (await api.get('/api/rbac/users')).data.items
    }
    if (canPlans.value) {
      plans.value = (await api.get('/api/rbac/plans')).data.items
    }
    if (canMenus.value) {
      menus.value = (await api.get('/api/rbac/menu-modules')).data.items
    }
  } finally {
    loading.value = false
  }
}

onMounted(reloadAll)

// ---- users modal ----
const showUser = ref(false)
const editingUserId = ref<number | null>(null)
const userEmail = ref('')
const userPassword = ref('')
const userIsAdmin = ref(false)
const userRoles = ref<string[]>([])

const roleOptions = computed(() => roles.value.map((r) => ({ label: `${r.name} (${r.code})`, value: r.code })))

function openCreateUser() {
  editingUserId.value = null
  userEmail.value = ''
  userPassword.value = ''
  userIsAdmin.value = false
  userRoles.value = []
  showUser.value = true
}

function openEditUser(row: any) {
  editingUserId.value = row.id
  userEmail.value = row.email
  userPassword.value = ''
  userIsAdmin.value = !!row.is_admin
  userRoles.value = row.roles ?? []
  showUser.value = true
}

async function saveUser() {
  if (!canUsers.value) return
  if (!userEmail.value.trim()) return message.error('账号不能为空')
  if (editingUserId.value == null) {
    await api.post('/api/rbac/users', {
      email: userEmail.value,
      password: userPassword.value || '123456',
      roles: userRoles.value,
      is_admin: userIsAdmin.value
    })
    message.success('已创建用户')
  } else {
    await api.put(`/api/rbac/users/${editingUserId.value}`, {
      password: userPassword.value || null,
      roles: userRoles.value,
      is_admin: userIsAdmin.value
    })
    message.success('已更新用户')
  }
  showUser.value = false
  await reloadAll()
}

const userColumns = [
  { title: 'ID', key: 'id', width: 80 },
  { title: '账号', key: 'email' },
  {
    title: '管理员',
    key: 'is_admin',
    width: 90,
    render: (row: any) => h(NTag, { size: 'small', type: row.is_admin ? 'success' : 'default' }, { default: () => (row.is_admin ? '是' : '否') })
  },
  {
    title: '角色',
    key: 'roles',
    render: (row: any) =>
      h('div', { style: 'display:flex; gap:6px; flex-wrap:wrap' }, (row.roles ?? []).map((x: string) => h(NTag, { size: 'small' }, { default: () => x })))
  },
  {
    title: '操作',
    key: 'actions',
    width: 140,
    render: (row: any) =>
      h(NButton, { size: 'small', secondary: true, disabled: !canUsers.value, onClick: () => openEditUser(row) }, { default: () => '编辑' })
  }
]

// ---- roles modal ----
const showRole = ref(false)
const roleEditingId = ref<number | null>(null)
const roleCode = ref('')
const roleName = ref('')
const rolePerms = ref<string[]>([])

const permOptions = computed(() => permissions.value.map((p) => ({ label: `${p.code}（${p.name}）`, value: p.code })))

function openCreateRole() {
  roleEditingId.value = null
  roleCode.value = ''
  roleName.value = ''
  rolePerms.value = []
  showRole.value = true
}

function openEditRole(row: any) {
  roleEditingId.value = row.id
  roleCode.value = row.code
  roleName.value = row.name
  rolePerms.value = row.permissions ?? []
  showRole.value = true
}

async function saveRole() {
  if (!canRoles.value) return
  if (!roleCode.value.trim() || !roleName.value.trim()) return message.error('code/name 不能为空')
  if (roleEditingId.value == null) {
    await api.post('/api/rbac/roles', { code: roleCode.value, name: roleName.value, permissions: rolePerms.value })
    message.success('已创建角色')
  } else {
    await api.put(`/api/rbac/roles/${roleEditingId.value}`, { name: roleName.value, permissions: rolePerms.value })
    message.success('已更新角色')
  }
  showRole.value = false
  await reloadAll()
}

const roleColumns = [
  { title: 'ID', key: 'id', width: 80 },
  { title: 'code', key: 'code', width: 140 },
  { title: '名称', key: 'name' },
  { title: '权限数', key: 'permissions', width: 90, render: (row: any) => String((row.permissions ?? []).length) },
  {
    title: '操作',
    key: 'actions',
    width: 140,
    render: (row: any) =>
      h(NButton, { size: 'small', secondary: true, disabled: !canRoles.value, onClick: () => openEditRole(row) }, { default: () => '编辑' })
  }
]

// ---- plans modal ----
const showPlan = ref(false)
const planCode = ref('')
const planName = ref('')
const planCurrency = ref('CNY')
const planMonth = ref<number | null>(0)
const planQuarter = ref<number | null>(0)
const planYear = ref<number | null>(0)
const planActive = ref(true)

function openEditPlan(row: any) {
  planCode.value = row.code
  planName.value = row.name
  planCurrency.value = row.currency || 'CNY'
  planMonth.value = Number(row.price_month ?? 0)
  planQuarter.value = Number(row.price_quarter ?? 0)
  planYear.value = Number(row.price_year ?? 0)
  planActive.value = !!row.active
  showPlan.value = true
}

async function savePlan() {
  if (!canPlans.value) return
  await api.post('/api/rbac/plans', {
    code: planCode.value,
    name: planName.value,
    currency: planCurrency.value,
    price_month: planMonth.value ?? 0,
    price_quarter: planQuarter.value ?? 0,
    price_year: planYear.value ?? 0,
    active: planActive.value
  })
  message.success('已保存套餐')
  showPlan.value = false
  await reloadAll()
}

const planColumns = [
  { title: 'code', key: 'code', width: 120 },
  { title: '名称', key: 'name' },
  { title: '月', key: 'price_month', width: 90 },
  { title: '季', key: 'price_quarter', width: 90 },
  { title: '年', key: 'price_year', width: 90 },
  { title: '币种', key: 'currency', width: 80 },
  { title: '启用', key: 'active', width: 80, render: (row: any) => (row.active ? '是' : '否') },
  {
    title: '操作',
    key: 'actions',
    width: 120,
    render: (row: any) =>
      h(NButton, { size: 'small', secondary: true, disabled: !canPlans.value, onClick: () => openEditPlan(row) }, { default: () => '编辑' })
  }
]

// ---- menus modal ----
const showMenu = ref(false)
const menuKey = ref('')
const menuLabel = ref('')
const menuPath = ref('')
const menuIcon = ref<string | null>(null)
const menuPerm = ref<string | null>(null)
const menuSort = ref<number | null>(100)
const menuEnabled = ref(true)

function openEditMenu(row: any) {
  menuKey.value = row.key
  menuLabel.value = row.label
  menuPath.value = row.path
  menuIcon.value = row.icon ?? null
  menuPerm.value = row.permission_code ?? null
  menuSort.value = row.sort_order ?? 100
  menuEnabled.value = !!row.enabled
  showMenu.value = true
}

async function saveMenu() {
  if (!canMenus.value) return
  await api.post('/api/rbac/menu-modules', {
    key: menuKey.value,
    label: menuLabel.value,
    path: menuPath.value,
    icon: menuIcon.value,
    permission_code: menuPerm.value,
    sort_order: menuSort.value ?? 100,
    enabled: menuEnabled.value
  })
  message.success('已保存菜单')
  showMenu.value = false
  await reloadAll()
}

const menuColumns = [
  { title: 'key', key: 'key', width: 140 },
  { title: '标题', key: 'label', width: 140 },
  { title: '路径', key: 'path' },
  { title: '权限', key: 'permission_code', width: 220 },
  { title: '排序', key: 'sort_order', width: 80 },
  { title: '启用', key: 'enabled', width: 80, render: (row: any) => (row.enabled ? '是' : '否') },
  {
    title: '操作',
    key: 'actions',
    width: 120,
    render: (row: any) =>
      h(NButton, { size: 'small', secondary: true, disabled: !canMenus.value, onClick: () => openEditMenu(row) }, { default: () => '编辑' })
  }
]
</script>

<template>
  <NCard class="panel" size="small">
    <template #header>用户与权限</template>
    <NTabs v-model:value="tab" type="segment">
      <NTabPane name="users" tab="用户" v-if="canUsers">
        <div style="display:flex; justify-content:flex-end; margin-bottom: 10px">
          <NButton type="primary" @click="openCreateUser">新增用户</NButton>
        </div>
        <NDataTable :columns="userColumns" :data="users" :loading="loading" />
      </NTabPane>
      <NTabPane name="roles" tab="角色" v-if="canRoles">
        <div style="display:flex; justify-content:flex-end; margin-bottom: 10px">
          <NButton type="primary" @click="openCreateRole">新增角色</NButton>
        </div>
        <NDataTable :columns="roleColumns" :data="roles" :loading="loading" />
      </NTabPane>
      <NTabPane name="plans" tab="套餐" v-if="canPlans">
        <NDataTable :columns="planColumns" :data="plans" :loading="loading" />
      </NTabPane>
      <NTabPane name="menus" tab="菜单" v-if="canMenus">
        <NDataTable :columns="menuColumns" :data="menus" :loading="loading" />
      </NTabPane>
      <NTabPane name="no" tab="无权限" v-if="!canUsers && !canRoles && !canPlans && !canMenus">
        你没有用户/角色/菜单/套餐管理权限。
      </NTabPane>
    </NTabs>
  </NCard>

  <NModal v-model:show="showUser" preset="card" title="用户" class="modal">
    <NForm>
      <NFormItem label="账号">
        <NInput v-model:value="userEmail" :disabled="editingUserId != null" />
      </NFormItem>
      <NFormItem label="密码（可空）">
        <NInput v-model:value="userPassword" type="password" placeholder="不填则不改/默认 123456" />
      </NFormItem>
      <NFormItem label="管理员">
        <NSwitch v-model:value="userIsAdmin" />
      </NFormItem>
      <NFormItem label="角色">
        <NSelect v-model:value="userRoles" multiple filterable :options="roleOptions" />
      </NFormItem>
      <div style="display:flex; justify-content:flex-end; gap:10px">
        <NButton secondary @click="showUser = false">取消</NButton>
        <NButton type="primary" @click="saveUser">保存</NButton>
      </div>
    </NForm>
  </NModal>

  <NModal v-model:show="showRole" preset="card" title="角色" class="modal">
    <NForm>
      <NFormItem label="code">
        <NInput v-model:value="roleCode" :disabled="roleEditingId != null" />
      </NFormItem>
      <NFormItem label="名称">
        <NInput v-model:value="roleName" />
      </NFormItem>
      <NFormItem label="权限">
        <NSelect v-model:value="rolePerms" multiple filterable :options="permOptions" />
      </NFormItem>
      <div style="display:flex; justify-content:flex-end; gap:10px">
        <NButton secondary @click="showRole = false">取消</NButton>
        <NButton type="primary" @click="saveRole">保存</NButton>
      </div>
    </NForm>
  </NModal>

  <NModal v-model:show="showPlan" preset="card" title="套餐" class="modal">
    <NForm>
      <NFormItem label="code"><NInput v-model:value="planCode" disabled /></NFormItem>
      <NFormItem label="名称"><NInput v-model:value="planName" /></NFormItem>
      <NFormItem label="币种"><NInput v-model:value="planCurrency" /></NFormItem>
      <NFormItem label="月"><NInputNumber v-model:value="planMonth" /></NFormItem>
      <NFormItem label="季"><NInputNumber v-model:value="planQuarter" /></NFormItem>
      <NFormItem label="年"><NInputNumber v-model:value="planYear" /></NFormItem>
      <NFormItem label="启用"><NSwitch v-model:value="planActive" /></NFormItem>
      <div style="display:flex; justify-content:flex-end; gap:10px">
        <NButton secondary @click="showPlan = false">取消</NButton>
        <NButton type="primary" @click="savePlan">保存</NButton>
      </div>
    </NForm>
  </NModal>

  <NModal v-model:show="showMenu" preset="card" title="菜单" class="modal">
    <NForm>
      <NFormItem label="key"><NInput v-model:value="menuKey" disabled /></NFormItem>
      <NFormItem label="标题"><NInput v-model:value="menuLabel" /></NFormItem>
      <NFormItem label="路径"><NInput v-model:value="menuPath" /></NFormItem>
      <NFormItem label="icon"><NInput v-model:value="menuIcon" placeholder="可选" /></NFormItem>
      <NFormItem label="权限"><NSelect v-model:value="menuPerm" clearable filterable :options="permOptions" /></NFormItem>
      <NFormItem label="排序"><NInputNumber v-model:value="menuSort" /></NFormItem>
      <NFormItem label="启用"><NSwitch v-model:value="menuEnabled" /></NFormItem>
      <div style="display:flex; justify-content:flex-end; gap:10px">
        <NButton secondary @click="showMenu = false">取消</NButton>
        <NButton type="primary" @click="saveMenu">保存</NButton>
      </div>
    </NForm>
  </NModal>
</template>

<style scoped>
.panel {
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.06);
  backdrop-filter: blur(10px);
}
.modal {
  width: min(720px, 94vw);
  border: 1px solid rgba(255, 255, 255, 0.12);
  background: rgba(20, 20, 24, 0.85);
  backdrop-filter: blur(12px);
}
</style>

