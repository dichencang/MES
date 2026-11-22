/** 后端时间串统一格式化。
 * 契约里时间是 ISO 8601 带时区，如 2026-11-17T21:35:41.099120+08:00。
 * 这里按字符串截取到秒并去掉 T，不做时区换算——后端返回的已是本地时区时间。
 */
export function formatDateTime(value?: string | null): string {
  if (!value) return '—'
  const m = value.match(/^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})/)
  return m ? `${m[1]} ${m[2]}` : value
}

/**
 * ISO 8601 UTC Z → Asia/Shanghai 展示（契约-计划管理 §一）。
 * 计划管理的时间字段是 UTC Z（…Z），必须 +8 小时到上海时间再展示。
 * 用 Intl 指定 timeZone，避免依赖浏览器本地时区。
 */
export function formatUtcShanghai(value?: string | null): string {
  if (!value) return '—'
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  const parts = new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', hour12: false,
  }).formatToParts(d)
  const get = (t: string) => parts.find((p) => p.type === t)?.value ?? ''
  return `${get('year')}-${get('month')}-${get('day')} ${get('hour')}:${get('minute')}`
}

/** datetime-local 的本地时间字符串 → ISO 8601 UTC Z 提交（契约要求请求也用 UTC Z） */
export function localInputToUtcZ(localValue: string): string {
  if (!localValue) return ''
  const d = new Date(localValue)
  return Number.isNaN(d.getTime()) ? localValue : d.toISOString().replace(/\.\d{3}Z$/, 'Z')
}

/** 后端 UTC Z → datetime-local 输入值（本地时区），用于编辑回显 */
export function utcZToLocalInput(value: string | null | undefined): string {
  if (!value) return ''
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}
