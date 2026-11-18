// 权限编码常量。与已冻结契约 v1.0 一一对应：一个接口 = 一个编码。
// 页面里禁止再写裸字符串（裸串拼错不会报错，按钮会静默消失），统一用 PERM.xxx 引用。
// 新模块追加时按 `模块:资源:动作` 续写，动作只用 list/create/update/delete/query/export/assign 等既有动词。

export const PERM = {
  user: {
    list: 'system:user:list',
    create: 'system:user:create',
    update: 'system:user:update',
    delete: 'system:user:delete',
    resetPassword: 'system:user:reset-password',
    setStatus: 'system:user:set-status',
    assignRoles: 'system:user:assign-roles',
  },
  role: {
    list: 'system:role:list',
    create: 'system:role:create',
    update: 'system:role:update',
    delete: 'system:role:delete',
    /** 授权回显（GET /roles/{id}/permissions） */
    query: 'system:role:query',
    /** 授权保存（PUT /roles/{id}/permissions），读写分离 */
    assignPermissions: 'system:role:assign-permissions',
    setDataScope: 'system:role:set-data-scope',
  },
  permission: {
    list: 'system:permission:list',
    create: 'system:permission:create',
    update: 'system:permission:update',
    delete: 'system:permission:delete',
  },
  dept: {
    list: 'system:dept:list',
    create: 'system:dept:create',
    update: 'system:dept:update',
    delete: 'system:dept:delete',
  },
  /** 字典：类型与项并入第三段，用 type- / item- 前缀区分 */
  dict: {
    typeList: 'system:dict:type-list',
    typeCreate: 'system:dict:type-create',
    typeUpdate: 'system:dict:type-update',
    typeDelete: 'system:dict:type-delete',
    itemList: 'system:dict:item-list',
    itemCreate: 'system:dict:item-create',
    itemUpdate: 'system:dict:item-update',
    itemDelete: 'system:dict:item-delete',
  },
  config: {
    list: 'system:config:list',
    query: 'system:config:query',
    create: 'system:config:create',
    update: 'system:config:update',
    delete: 'system:config:delete',
  },
  operLog: {
    list: 'system:oper-log:list',
    query: 'system:oper-log:query',
    clear: 'system:oper-log:clear',
  },
} as const

export type PermCode = string
