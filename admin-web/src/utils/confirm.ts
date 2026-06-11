import { ElMessageBox } from 'element-plus'

type DangerConfirmOptions = {
  title?: string
  confirmButtonText?: string
}

export function confirmDanger(message: string, options: DangerConfirmOptions = {}) {
  return ElMessageBox.confirm(message, options.title ?? '确认删除', {
    appendTo: document.body,
    customClass: 'confirm-dialog',
    confirmButtonText: options.confirmButtonText ?? '删除',
    cancelButtonText: '取消',
    type: 'warning',
    center: false,
    draggable: false,
  })
}
