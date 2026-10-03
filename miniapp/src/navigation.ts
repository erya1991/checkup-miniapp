export const tabPaths = { home: '/pages/index/index', reports: '/pages/reports/index', mine: '/pages/mine/index' }
export type ReportView = 'reports' | 'metrics'
export function newUploadPath() { return '/pages/upload/index?new=1' }
export function openReports(view: ReportView = 'reports') {
  uni.setStorageSync('uiReportView', view)
  uni.switchTab({ url: tabPaths.reports })
}
export function navigate(url: string) {
  if (url.split('?')[0] === '/pages/profile-metrics/index') return openReports('metrics')
  if (Object.values(tabPaths).includes(url)) {
    if (url === tabPaths.reports) return openReports()
    return uni.switchTab({ url })
  }
  return uni.navigateTo({ url })
}
