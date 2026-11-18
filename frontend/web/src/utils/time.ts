/** 后端时间串统一格式化。
 * 契约里时间是 ISO 8601 带时区，如 2026-11-17T21:35:41.099120+08:00。
 * 这里按字符串截取到秒并去掉 T，不做时区换算——后端返回的已是本地时区时间。
 */
export function formatDateTime(value?: string | null): string {
  if (!value) return '—'
  const m = value.match(/^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}:\d{2})/)
  return m ? `${m[1]} ${m[2]}` : value
}
