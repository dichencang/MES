// 系统管理模块类型定义。字段与已冻结契约 v1.0 一致：camelCase / ID 字符串 / status·visible 为 "0"·"1"。

export interface ApiResult<T> {
  code: number
  message: string
  data: T
}

export interface PageResult<T> {
  total: number
  list: T[]
}

export interface PageQuery {
  page: number
  pageSize: number
  sort?: string
}

/** 权限树节点（/permissions/my 的 tree 只含 DIR/MENU，BUTTON 只在管理树里出现） */
export interface PermNode {
  id: string
  parentId: string
  permName: string
  permType: 'DIR' | 'MENU' | 'BUTTON'
  permissionCode: string
  path: string | null
  component: string | null
  icon: string | null
  orderNum: number
  visible: '0' | '1'
  status: '0' | '1'
  children: PermNode[]
}

/** GET /permissions/my 响应 */
export interface MyPermissions {
  tree: PermNode[]
  permissionCodes: string[]
}

/** GET /auth/login|refresh 响应 data */
export interface AuthSession {
  accessToken: string
  refreshToken: string
  expiresIn: number
}

/** POST /auth/login 请求体（图片验证码为必填） */
export interface LoginPayload {
  username: string
  password: string
  captchaId: string
  captchaCode: string
}

/** GET /auth/captcha 响应 data：image 为 PNG data URL，expiresIn 单位秒 */
export interface CaptchaResult {
  captchaId: string
  image: string
  expiresIn: number
}

/** GET /auth/me 响应 data */
export interface UserInfo {
  id: string
  username: string
  realName: string
  deptId: string
  deptName: string | null
  roleCodes: string[]
  roles: Array<{ id: string; roleCode: string; roleName: string }>
  isSuper: boolean
}

/** 用户列表行（直接作为编辑表单数据源，不设详情接口） */
export interface UserItem {
  id: string
  username: string
  realName: string
  deptId: string
  deptName: string | null
  phone: string | null
  email: string | null
  status: '0' | '1'
  isBuiltin: '0' | '1'
  roles: Array<{ id: string; roleCode: string; roleName: string }>
  createTime: string
}

export interface UserQuery extends PageQuery {
  username?: string
  realName?: string
  deptId?: string
  status?: '0' | '1'
}

export interface UserUpsert {
  username: string
  realName: string
  password: string
  deptId: string
  roleIds: string[]
  phone: string | null
  email: string | null
  status: '0' | '1'
}

/** 角色列表行 */
export interface RoleItem {
  id: string
  roleCode: string
  roleName: string
  dataScope: 'ALL' | 'CUSTOM' | 'DEPT' | 'DEPT_CHILD' | 'SELF'
  deptIds: string[]
  isSuper: '0' | '1'
  remark: string | null
  createTime: string
}

export interface RoleUpsert {
  roleCode: string
  roleName: string
  dataScope: RoleItem['dataScope']
  deptIds: string[]
  remark: string | null
}

/** 权限管理树节点（GET /permissions/tree，含 status） */
export interface PermissionItem extends PermNode {
  status: '0' | '1'
}

export interface DeptNode {
  id: string
  parentId: string
  deptName: string
  orderNum: number
  leader: string | null
  phone: string | null
  status: '0' | '1'
}

export interface DictType {
  id: string
  dictCode: string
  dictName: string
  status: '0' | '1'
  remark: string | null
}

export interface DictDataItem {
  id: string
  dictCode: string
  dictLabel: string
  dictValue: string
  orderNum: number
  status: '0' | '1'
}

/** 业务公共下拉 GET /dict-data/{dictCode} 的项 */
export interface DictOption {
  dictLabel: string
  dictValue: string
}

export interface ConfigItem {
  id: string
  configName: string
  configKey: string
  configValue: string
  configType: '0' | '1'
  remark: string | null
}

export interface OperLog {
  id: string
  operatorId: string
  operatorName: string
  module: string
  operation: string
  requestUrl: string
  ip: string
  status: '0' | '1'
  costTime: number
  operTime: string
  method?: string
  requestParam?: string | null
  errorMsg?: string | null
}

export interface OperLogQuery extends PageQuery {
  operatorName?: string
  module?: string
  startTime?: string
  endTime?: string
  status?: '0' | '1'
}
