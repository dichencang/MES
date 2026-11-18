// 全局常量。枚举值与已冻结契约一致：status / visible / isBuiltin / configType 均为字符串 "0"·"1"。

export const APP_TITLE = import.meta.env.VITE_APP_TITLE || 'MES 生产执行系统'

/** 分页：契约固定 page 从 1 开始，默认 10，最大 100 */
export const PAGE_DEFAULT_SIZE = 10
export const PAGE_MAX_SIZE = 100
export const PAGE_SIZES = [10, 20, 50, 100] as const

/** 通用状态：0 正常 / 1 停用 */
export const STATUS_ENABLED = '0'
export const STATUS_DISABLED = '1'
export const STATUS_OPTIONS = [
  { label: '正常', value: STATUS_ENABLED },
  { label: '停用', value: STATUS_DISABLED },
] as const

/** 菜单可见性：0 显示 / 1 隐藏（隐藏仍注册路由） */
export const VISIBLE_SHOW = '0'
export const VISIBLE_HIDE = '1'

/** 内置资源标记 */
export const BUILTIN_YES = '0'
export const BUILTIN_NO = '1'

/** 角色数据范围 */
export const DATA_SCOPE_OPTIONS = [
  { label: '全部数据', value: 'ALL' },
  { label: '本部门', value: 'DEPT' },
  { label: '本部门及下级', value: 'DEPT_CHILD' },
  { label: '仅本人', value: 'SELF' },
  { label: '自定义部门', value: 'CUSTOM' },
] as const
export type DataScope = (typeof DATA_SCOPE_OPTIONS)[number]['value']

/** 权限节点类型 */
export const PERM_TYPE_OPTIONS = [
  { label: '目录', value: 'DIR' },
  { label: '菜单', value: 'MENU' },
  { label: '按钮', value: 'BUTTON' },
] as const

/** 系统参数类型：0 内置（不可删）/ 1 自定义 */
export const CONFIG_BUILTIN = '0'
export const CONFIG_CUSTOM = '1'

/** 操作日志结果：0 成功 / 1 失败 */
export const LOG_SUCCESS = '0'
export const LOG_FAIL = '1'
export const LOG_STATUS_OPTIONS = [
  { label: '成功', value: LOG_SUCCESS },
  { label: '失败', value: LOG_FAIL },
] as const

/** localStorage 键（请求层与状态层共用，避免各写一份） */
export const STORAGE_KEYS = {
  accessToken: 'mes_access_token',
  refreshToken: 'mes_refresh_token',
} as const

/** 会话失效事件：请求层派发，路由层监听后清状态跳登录 */
export const EVENT_UNAUTHORIZED = 'mes:unauthorized'

/** 日期时间展示：统一把后端 ISO 串截成秒级 */
export const DATETIME_FORMAT = 'YYYY-MM-DD HH:mm:ss'
export const DATE_FORMAT = 'YYYY-MM-DD'
