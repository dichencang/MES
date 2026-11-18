// 通用列表页 CRUD：分页查询 + 弹窗表单 + 增改删，消灭每页复制一遍的同构代码。
// 用法见 views/system/config/index.vue（样板）。树形页（部门/权限/字典）只需 load 部分，不必用表单部分。
import { reactive, ref, type Ref } from 'vue'
import { ElMessage } from 'element-plus'
import { PAGE_DEFAULT_SIZE } from '@/constants'
import { confirmDelete } from '@/utils/confirm'
import type { PageResult } from '@/types'

type AnyForm = Record<string, any>

export interface CrudOptions<T extends { id: string }, F extends AnyForm = AnyForm> {
  /** 列表接口，入参已自动剔除空值 */
  fetch: (params: Record<string, unknown>) => Promise<PageResult<T>>
  /** 查询条件初始值（不含 page/pageSize，会自动补） */
  defaultQuery?: () => AnyForm
  /** 表单初始值 */
  defaultForm?: () => F
  create?: (data: AnyForm) => Promise<unknown>
  update?: (id: string, data: AnyForm) => Promise<unknown>
  remove?: (id: string) => Promise<unknown>
  /** 行数据 → 表单数据（行里字段与表单不一致时用，如 roleIds 由 roles 提取） */
  toForm?: (row: T) => AnyForm
  /** 表单 → 提交体（需要剔字段、转 null 时用） */
  toPayload?: (form: F, editing: boolean) => AnyForm
  /** 提交前校验，返回 false 则中止（如 el-form 校验、必填拦截） */
  beforeSubmit?: (form: F, editing: boolean) => boolean | Promise<boolean>
  /** 删除确认文案 */
  describe?: (row: T) => string
  /** 新增/编辑成功文案 */
  successText?: { create?: string; update?: string }
}

export function useCrud<T extends { id: string }, F extends AnyForm = AnyForm>(opts: CrudOptions<T, F>) {
  const loading = ref(false)
  const rows = ref<T[]>([]) as Ref<T[]>
  const total = ref(0)
  const query = reactive<AnyForm>({ page: 1, pageSize: PAGE_DEFAULT_SIZE, ...(opts.defaultQuery?.() ?? {}) })

  const dialogVisible = ref(false)
  const editing = ref(false)
  const editingId = ref<string | null>(null)
  const submitting = ref(false)
  const form = reactive<AnyForm>(opts.defaultForm?.() ?? {}) as F

  /** 拉列表：空字符串/null/undefined 的查询条件不发给后端 */
  async function load() {
    loading.value = true
    try {
      const params: Record<string, unknown> = {}
      for (const [k, v] of Object.entries(query)) {
        if (v !== '' && v !== null && v !== undefined) params[k] = v
      }
      const res = await opts.fetch(params)
      rows.value = res.list
      total.value = res.total
    } finally {
      loading.value = false
    }
  }

  /** 点查询：回到第一页 */
  function search() {
    query.page = 1
    return load()
  }

  /** 重置条件并回到第一页 */
  function resetQuery() {
    const fresh = opts.defaultQuery?.() ?? {}
    for (const key of Object.keys(query)) {
      if (key !== 'page' && key !== 'pageSize') delete query[key]
    }
    Object.assign(query, fresh)
    query.page = 1
    return load()
  }

  function openCreate() {
    editing.value = false
    editingId.value = null
    Object.assign(form, opts.defaultForm?.() ?? {})
    dialogVisible.value = true
  }

  function openEdit(row: T) {
    editing.value = true
    editingId.value = row.id
    Object.assign(form, opts.defaultForm?.() ?? {}, opts.toForm ? opts.toForm(row) : row)
    dialogVisible.value = true
  }

  async function submit() {
    if (opts.beforeSubmit) {
      const ok = await opts.beforeSubmit(form, editing.value)
      if (!ok) return
    }
    const payload = opts.toPayload ? opts.toPayload(form, editing.value) : { ...form }
    submitting.value = true
    try {
      if (editing.value && editingId.value) {
        await opts.update?.(editingId.value, payload)
        ElMessage.success(opts.successText?.update ?? '已保存')
      } else {
        await opts.create?.(payload)
        ElMessage.success(opts.successText?.create ?? '已创建')
      }
      dialogVisible.value = false
      await load()
    } finally {
      submitting.value = false
    }
  }

  async function remove(row: T) {
    await confirmDelete(opts.describe?.(row))
    await opts.remove?.(row.id)
    ElMessage.success('已删除')
    await load()
  }

  return {
    loading, rows, total, query,
    dialogVisible, editing, editingId, submitting, form,
    load, search, resetQuery, openCreate, openEdit, submit, remove,
  }
}
