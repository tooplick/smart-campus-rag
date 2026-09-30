import axios from 'axios'
import { getToken, getClientId, clearToken } from './auth'

/** API 错误:携带业务错误码与 HTTP 状态 */
export class ApiError extends Error {
  code: string
  status: number
  constructor(message: string, code: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
  }
}

/** 将后端两种错误形态统一为 ApiError */
export function normalizeError(status: number, body: unknown): ApiError {
  if (body && typeof body === 'object') {
    const b = body as Record<string, any>
    if (b.success === false) {
      return new ApiError(b.message || '请求失败', b.error?.code || `HTTP_${status}`, status)
    }
    if (b.detail !== undefined) {
      const msg = typeof b.detail === 'string' ? b.detail : JSON.stringify(b.detail)
      return new ApiError(msg, `HTTP_${status}`, status)
    }
    if (typeof b.message === 'string') {
      return new ApiError(b.message, `HTTP_${status}`, status)
    }
  }
  return new ApiError(`请求失败(HTTP ${status})`, `HTTP_${status}`, status)
}

/** 错误码 → 用户可读文案,未命中回退原始消息 */
const ERROR_MESSAGES: Record<string, string> = {
  MISSING_CLIENT_ID: '会话标识缺失,请刷新页面重试',
  EMPTY_MESSAGE: '请输入问题内容',
  MESSAGE_TOO_LONG: '问题长度不能超过 2000 字',
  INVALID_KNOWLEDGE_BASE: '所选知识库不可用(不存在、已禁用或正在建立索引)',
  CONVERSATION_NOT_FOUND: '会话不存在或已删除',
  RAG_NOT_READY: '知识库尚未就绪,请稍后再试',
  LLM_ERROR: '模型服务出错,请稍后再试',
  INVALID_CREDENTIALS: '用户名或密码错误',
  ADMIN_NOT_INITIALIZED: '管理员尚未初始化',
  ADMIN_DISABLED: '管理员账号已禁用',
  PASSWORD_TOO_SHORT: '新密码长度至少 6 位',
  INVALID_CURRENT_PASSWORD: '当前密码错误',
  INVALID_OLD_PASSWORD: '原密码错误',
  DOC_PROCESSING: '文档正在处理中,暂不可执行该操作',
  DOC_NOT_PROCESSING: '文档当前不在处理中',
  UPLOAD_ERROR: '上传失败,请检查文件后重试',
  NETWORK_ERROR: '网络错误,请检查连接后重试',
}

export function errorMessage(err: unknown): string {
  if (err instanceof ApiError) return ERROR_MESSAGES[err.code] || err.message
  if (err instanceof Error) return err.message
  return '未知错误'
}

const request = axios.create({ baseURL: '/api', timeout: 30000 })

request.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  const clientId = getClientId()
  if (clientId) config.headers['X-Client-ID'] = clientId
  return config
})

request.interceptors.response.use(
  (res) => {
    const body = res.data
    if (body && typeof body === 'object' && 'success' in body) {
      if (body.success) return body.data
      return Promise.reject(normalizeError(res.status, body))
    }
    return body
  },
  (err) => {
    if (err.response) {
      if (err.response.status === 401 && location.pathname.startsWith('/admin')
        && !location.pathname.includes('login')) {
        clearToken()
        location.href = '/admin/login'
      }
      return Promise.reject(normalizeError(err.response.status, err.response.data))
    }
    return Promise.reject(new ApiError('网络错误,请检查连接后重试', 'NETWORK_ERROR', 0))
  },
)

/** fetch 版 JSON 请求(会话类接口,带 X-Client-ID),与 axios 共享错误归一化 */
export async function jsonFetch<T>(path: string, init: RequestInit = {}): Promise<T> {
  // 用 Headers 构建,避免把任意 headers 断言成 Record 的类型谎言
  const headers = new Headers(init.headers)
  if (!headers.has('Content-Type')) headers.set('Content-Type', 'application/json')
  const clientId = getClientId()
  if (clientId) headers.set('X-Client-ID', clientId)
  let res: Response
  try {
    // 去掉前导斜杠再拼接,防止 path 不带 / 时拼成 /apixxx
    res = await fetch(`/api/${path.replace(/^\//, '')}`, { ...init, headers })
  } catch {
    throw new ApiError('网络错误,请检查连接后重试', 'NETWORK_ERROR', 0)
  }
  const body = await res.json().catch(() => null)
  if (!res.ok) throw normalizeError(res.status, body)
  if (body && typeof body === 'object' && 'success' in body) {
    if (body.success) return body.data as T
    throw normalizeError(res.status, body)
  }
  return body as T
}

export default request
