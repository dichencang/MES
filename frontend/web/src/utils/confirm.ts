// 统一二次确认。删除类操作统一走 confirmDelete，文案带对象名，避免手写各处措辞不一致。
import { ElMessageBox } from 'element-plus'

export function confirmAction(message: string, title = '提示') {
  return ElMessageBox.confirm(message, title, { type: 'warning', confirmButtonText: '确定', cancelButtonText: '取消' })
}

export function confirmDelete(name?: string) {
  return confirmAction(`确认删除${name ? `「${name}」` : '该记录'}？删除后不可恢复。`)
}
