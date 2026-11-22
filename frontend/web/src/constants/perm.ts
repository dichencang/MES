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
  /** 基础数据（契约-基础数据 v1.2 §九）。物料无 query：编辑用弹窗、列表返回全字段 */
  basic: {
    material: {
      list: 'basic:material:list',
      create: 'basic:material:create',
      update: 'basic:material:update',
      setStatus: 'basic:material:set-status',
    },
    process: {
      list: 'basic:process:list',
      create: 'basic:process:create',
      update: 'basic:process:update',
      setStatus: 'basic:process:set-status',
    },
    bom: {
      list: 'basic:bom:list',
      query: 'basic:bom:query',
      create: 'basic:bom:create',
      update: 'basic:bom:update',
      publish: 'basic:bom:publish',
      delete: 'basic:bom:delete',
    },
    routing: {
      list: 'basic:routing:list',
      query: 'basic:routing:query',
      create: 'basic:routing:create',
      update: 'basic:routing:update',
      publish: 'basic:routing:publish',
      delete: 'basic:routing:delete',
    },
  },
  /** 计划管理（契约-计划管理 v1.0 §六）。列表与详情有意复用 list 码；候选查询复用 create 码 */
  plan: {
    salesOrder: {
      list: 'plan:sales-order:list',
      create: 'plan:sales-order:create',
      update: 'plan:sales-order:update',
      cancel: 'plan:sales-order:cancel',
    },
    productionPlan: {
      list: 'plan:production-plan:list',
      create: 'plan:production-plan:create',
      update: 'plan:production-plan:update',
      cancel: 'plan:production-plan:cancel',
      transfer: 'plan:production-plan:transfer',
    },
    gantt: {
      list: 'plan:gantt:list',
    },
  },
  /** 生产工单（契约-生产工单 v1.0 §二）。详情与事件复用 list 码；complete/close 本期仅预留 */
  workorder: {
    list: 'workorder:list',
    create: 'workorder:create',
    update: 'workorder:update',
    release: 'workorder:release',
    assign: 'workorder:assign',
    start: 'workorder:start',
    cancel: 'workorder:cancel',
    complete: 'workorder:complete',
    close: 'workorder:close',
    gantt: {
      list: 'workorder:gantt:list',
    },
  },
} as const

export type PermCode = string
