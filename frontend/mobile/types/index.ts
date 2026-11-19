// 移动端类型定义。字段与已冻结契约一致，与 Web 端 types/index.ts 同源。

export interface ApiResult<T> {
  code: number
  message: string
  data: T
}

export interface PageResult<T> {
  total: number
  list: T[]
}

export interface AuthSession {
  accessToken: string
  refreshToken: string
  expiresIn: number
}

export interface LoginPayload {
  username: string
  password: string
  captchaId: string
  captchaCode: string
}

export interface CaptchaResult {
  captchaId: string
  image: string
  expiresIn: number
}

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

export interface MyPermissions {
  tree: PermNode[]
  permissionCodes: string[]
}
