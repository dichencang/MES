// 系统管理接口。路径与请求体严格对照已冻结契约 v1.0；返回类型见 @/types。
// 约定：新增走 POST <资源>，编辑走 PUT <资源>/{id}，统一由 upsert 分发。
import { del, get, post, put } from '../request'
import type {
  ConfigItem, DeptNode, DictDataItem, DictOption, DictType,
  OperLog, PageResult, PermissionItem, RoleItem, UserItem,
} from '@/types'

/** 新增/编辑二合一：有 id 走 PUT，无 id 走 POST */
const upsert = <T>(base: string, data: Record<string, unknown>, id?: string) =>
  id ? put<T>(`${base}/${id}`, data) : post<T>(base, data)

// ── 用户 ───────────────────────────────────────────────
export const listUsers = (params: Record<string, unknown>) => get<PageResult<UserItem>>('/users', params)
export const saveUser = (data: Record<string, unknown>, id?: string) => upsert<null>('/users', data, id)
export const deleteUser = (id: string) => del<null>(`/users/${id}`)
export const resetPassword = (id: string, password: string) => put<null>(`/users/${id}/password`, { password })
export const setUserStatus = (id: string, status: '0' | '1') => put<null>(`/users/${id}/status`, { status })
export const assignUserRoles = (id: string, roleIds: string[]) => put<null>(`/users/${id}/roles`, { roleIds })

// ── 角色 ───────────────────────────────────────────────
export const listRoles = (params: Record<string, unknown>) => get<PageResult<RoleItem>>('/roles', params)
/** 下拉用全量角色（取前 100，契约上限即 100） */
export const allRoles = () => get<PageResult<RoleItem>>('/roles', { page: 1, pageSize: 100 })
export const saveRole = (data: Record<string, unknown>, id?: string) => upsert<null>('/roles', data, id)
export const deleteRole = (id: string) => del<null>(`/roles/${id}`)
export const getRolePermissions = (id: string) => get<{ permissionIds: string[] }>(`/roles/${id}/permissions`)
export const assignRolePermissions = (id: string, permissionIds: string[]) =>
  put<null>(`/roles/${id}/permissions`, { permissionIds })
export const setDataScope = (id: string, dataScope: string, deptIds: string[]) =>
  put<null>(`/roles/${id}/data-scope`, { dataScope, deptIds })

// ── 权限 ───────────────────────────────────────────────
export const getPermissionTree = (includeDisabled = false) =>
  get<PermissionItem[]>('/permissions/tree', { includeDisabled })
export const savePermission = (data: Record<string, unknown>, id?: string) => upsert<null>('/permissions', data, id)
export const deletePermission = (id: string) => del<null>(`/permissions/${id}`)

// ── 部门 ───────────────────────────────────────────────
export const getDeptTree = (includeDisabled = false) => get<DeptNode[]>('/depts/tree', { includeDisabled })
export const saveDept = (data: Record<string, unknown>, id?: string) => upsert<null>('/depts', data, id)
export const deleteDept = (id: string) => del<null>(`/depts/${id}`)

// ── 字典 ───────────────────────────────────────────────
export const listDictTypes = (params: Record<string, unknown>) => get<PageResult<DictType>>('/dict-types', params)
export const saveDictType = (data: Record<string, unknown>, id?: string) => upsert<null>('/dict-types', data, id)
export const deleteDictType = (id: string) => del<null>(`/dict-types/${id}`)
export const listDictData = (dictCode: string) => get<PageResult<DictDataItem>>('/dict-data', { dictCode })
/** 业务下拉：仅会话校验，返回启用项 [{ dictLabel, dictValue }] */
export const dictOptions = (dictCode: string) => get<DictOption[]>(`/dict-data/${dictCode}`)
export const saveDictData = (data: Record<string, unknown>, id?: string) => upsert<null>('/dict-data', data, id)
export const deleteDictData = (id: string) => del<null>(`/dict-data/${id}`)

// ── 系统参数 ───────────────────────────────────────────
export const listConfigs = (params: Record<string, unknown>) => get<PageResult<ConfigItem>>('/configs', params)
export const getConfigByKey = (key: string) => get<{ configKey: string; configValue: string }>(`/configs/key/${key}`)
export const saveConfig = (data: Record<string, unknown>, id?: string) => upsert<null>('/configs', data, id)
export const deleteConfig = (id: string) => del<null>(`/configs/${id}`)

// ── 操作日志 ───────────────────────────────────────────
export const listOperLogs = (params: Record<string, unknown>) => get<PageResult<OperLog>>('/oper-logs', params)
export const getOperLog = (id: string) => get<OperLog>(`/oper-logs/${id}`)
export const clearOperLogs = () => del<null>('/oper-logs')
