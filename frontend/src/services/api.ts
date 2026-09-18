import type { AnalysisResponse, FormatRequest, HealthResponse, PresetResponse, ReportResponse, StatusResponse, UploadResponse } from '../types'

const API_BASE_URL = import.meta.env.DEV
  ? (import.meta.env.VITE_API_BASE_URL ?? 'http://127.0.0.1:8000')
  : ''

export const api = {
  health: () => request<HealthResponse>('/api/health'),
  async getPresets() {
    const response = await request<{ profiles: PresetResponse[] }>('/api/presets')
    if (!Array.isArray(response.profiles) || response.profiles.length === 0) throw new Error('The backend returned no publication specifications.')
    for (const profile of response.profiles) {
      if (!profile.name || !profile.body_font || typeof profile.body_size_pt !== 'number' || typeof profile.body_line_spacing !== 'number') {
        throw new Error('The backend returned an invalid publication specification.')
      }
    }
    return response
  },
  async uploadDocument(file: File) { const form = new FormData(); form.append('file', file, file.name); return request<UploadResponse>('/api/documents/upload', { method: 'POST', body: form }) },
  analyzeDocument: (id: string) => request<AnalysisResponse>(`/api/documents/${id}/analyze`, { method: 'POST' }),
  formatDocument: (id: string, profile: string, model = 'logistic_regression') => { const body: FormatRequest = { profile, model }; return request<StatusResponse>(`/api/documents/${id}/format`, { method: 'POST', body: JSON.stringify(body), headers: { 'Content-Type': 'application/json' } }) },
  getDocumentStatus: (id: string) => request<StatusResponse>(`/api/documents/${id}/status`),
  getDocumentReport: (id: string) => request<ReportResponse>(`/api/documents/${id}/report`),
  async downloadDocument(id: string) { let response: Response; try { response = await fetch(`${API_BASE_URL}/api/documents/${id}/download`) } catch { throw new Error('DocXpress backend is unavailable.') } if (!response.ok) throw await readError(response); return { blob: await response.blob(), filename: filenameFromDisposition(response.headers.get('content-disposition')) } },
}

async function request<T>(path: string, options: RequestInit = {}) { let response: Response; try { response = await fetch(`${API_BASE_URL}${path}`, options) } catch { throw new Error('DocXpress backend is unavailable.') } if (!response.ok) throw await readError(response); try { return await response.json() as T } catch { throw new Error('DocXpress returned an invalid response.') } }
async function readError(response: Response) { try { const payload = await response.json() as { detail?: { message?: string } | string }; const detail = typeof payload.detail === 'string' ? payload.detail : payload.detail?.message; if (detail) return new Error(detail) } catch { /* Status fallback keeps the UI actionable. */ } return new Error(`DocXpress request failed (${response.status}).`) }
function filenameFromDisposition(header: string | null) { const match = header?.match(/filename="?([^";]+)"?/i); return match?.[1] ?? 'formatted-document.docx' }
