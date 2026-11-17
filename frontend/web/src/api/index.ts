// 接口封装。路径与请求体严格对照已冻结契约 v1.0；返回类型见 @/types。
import { del, get, post, put, tokenStore } from './request'
import type {
  AuthSession, ConfigItem, DeptNode, DictDataItem, DictOption, DictType,
  MyPermissions, OperLog, PageResult, PermissionItem, RoleItem, UserInfo, UserItem,
} from '@/types'

// 认证与会话
export const login = (username: string, password: string) =>
  post<AuthSession>('/auth/login', { username, password })
export const logout = () => post<null>('/auth/logout', { refreshToken: tokenStore.refresh })
export const getMe = () => get<UserInfo>('/auth/me')
export const changeOwnPassword = (oldPassword: string, newPassword: string) =>
  put<null>('/users/me/password', { oldPassword, newPassword })

// 权限
export const getMyPermissions = () => get<MyPermissions>('/permissions/my')
export const getPermissionTree = (includeDisabled = false) =>
  get<PermissionItem[]>('/permissions/tree', { includeDisabled })
export const savePermission = (data: Record<string, unknown>, id?: string) =>
  id ? put<null>(`/permissions/${id}`, data) : post<null>('/permissions', data)
export const deletePermission = (id: string) => del<null>(`/permissions/${id}`)

// 用户
export const listUsers = (params: Record<string, unknown>) => get<PageResult<UserItem>>('/users', params)
export const saveUser = (data: Record<string, unknown>, id?: string) =>
  id ? put<null>(`/users/${id}`, data) : post<null>('/users', data)
export const deleteUser = (id: string) => del<null>(`/users/${id}`)
export const resetPassword = (id: string, password: string) => put<null>(`/users/${id}/password`, { password })
export const setUserStatus = (id: string, status: '0' | '1') => put<null>(`/users/${id}/status`, { status })
export const assignUserRoles = (id: string, roleIds: string[]) => put<null>(`/users/${id}/roles`, { roleIds })

// 角色
export const listRoles = (params: Record<string, unknown>) => get<PageResult<RoleItem>>('/roles', params)
export const allRoles = () => get<PageResult<RoleItem>>('/roles', { page: 1, pageSize: 100 })
export const saveRole = (data: Record<string, unknown>, id?: string) =>
  id ? put<null>(`/roles/${id}`, data) : post<null>('/roles', data)
export const deleteRole = (id: string) => del<null>(`/roles/${id}`)
export const getRolePermissions = (id: string) => get<{ permissionIds: string[] }>(`/roles/${id}/permissions`)
export const assignRolePermissions = (id: string, permissionIds: string[]) =>
  put<null>(`/roles/${id}/permissions`, { permissionIds })
export const setDataScope = (id: string, dataScope: string, deptIds: string[]) =>
  put<null>(`/roles/${id}/data-scope`, { dataScope, deptIds })

// 部门
export const getDeptTree = (includeDisabled = false) => get<DeptNode[]>('/depts/tree', { includeDisabled })
export const saveDept = (data: Record<string, unknown>, id?: string) =>
  id ? put<null>(`/depts/${id}`, data) : post<null>('/depts', data)
export const deleteDept = (id: string) => del<null>(`/depts/${id}`)

// 字典
export const listDictTypes = (params: Record<string, unknown>) => get<PageResult<DictType>>('/dict-types', params)
export const saveDictType = (data: Record<string, unknown>, id?: string) =>
  id ? put<null>(`/dict-types/${id}`, data) : post<null>('/dict-types', data)
export const deleteDictType = (id: string) => del<null>(`/dict-types/${id}`)
export const listDictData = (dictCode: string) => get<PageResult<DictDataItem>>('/dict-data', { dictCode })
export const dictOptions = (dictCode: string) => get<DictOption[]>(`/dict-data/${dictCode}`)
export const saveDictData = (data: Record<string, unknown>, id?: string) =>
  id ? put<null>(`/dict-data/${id}`, data) : post<null>('/dict-data', data)
export const deleteDictData = (id: string) => del<null>(`/dict-data/${id}`)

// 系统参数
export const listConfigs = (params: Record<string, unknown>) => get<PageResult<ConfigItem>>('/configs', params)
export const getConfigByKey = (key: string) => get<{ configKey: string; configValue: string }>(`/configs/key/${key}`)
export const saveConfig = (data: Record<string, unknown>, id?: string) =>
  id ? put<null>(`/configs/${id}`, data) : post<null>('/configs', data)
export const deleteConfig = (id: string) => del<null>(`/configs/${id}`)

// 操作日志
export const listOperLogs = (params: Record<string, unknown>) => get<PageResult<OperLog>>('/oper-logs', params)
export const getOperLog = (id: string) => get<OperLog>(`/oper-logs/${id}`)
export const clearOperLogs = () => del<null>('/oper-logs')
