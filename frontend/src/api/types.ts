/** AUTO-EVO-AI API 类型定义 */
export interface ToolStatus {
  success?: boolean
  available: boolean
  name: string
  url?: string
  status?: string
  healthy?: boolean
  description?: string
  stars?: string
  [key: string]: any
}

export interface ModuleInfo {
  id?: string
  name?: string
  group?: string
  grade?: string
  version?: string
  real_logic?: boolean
  description?: string
  category?: string
  [key: string]: any
}

export interface SystemStatus {
  success: boolean
  system: string
  status: string
  modules_loaded: number
  modules_total: number
  modules_stub: number
  timestamp?: string
  coordinator?: Record<string, any>
  [key: string]: any
}
