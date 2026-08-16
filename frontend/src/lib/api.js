// DELETE endpoints require MIMIR_ADMIN_PASSWORD (see backend/app/auth.py
// require_admin) as a separate secret from the login session -- callers
// pass it in explicitly (e.g. typed into a confirm dialog) rather than it
// living anywhere in frontend state.
function adminHeader(adminPassword) {
  return adminPassword ? { 'X-Admin-Password': adminPassword } : {}
}

async function request(path, options = {}) {
  const res = await fetch(`/api${path}`, {
    credentials: 'include',
    ...options,
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
  })
  if (res.status === 401) {
    const err = new Error('unauthorized')
    err.status = 401
    throw err
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    const err = new Error(body.detail || `Request failed: ${res.status}`)
    err.status = res.status
    throw err
  }
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  login: (password) =>
    request('/auth/login', { method: 'POST', body: JSON.stringify({ password }) }),
  logout: () => request('/auth/logout', { method: 'POST' }),

  listEntries: ({ day, q, machine, projectId, sourceType } = {}) => {
    const params = new URLSearchParams()
    if (day) params.set('day', day)
    if (q) params.set('q', q)
    if (machine) params.set('machine', machine)
    if (projectId) params.set('project_id', projectId)
    if (sourceType) params.set('source_type', sourceType)
    const qs = params.toString()
    return request(`/entries${qs ? `?${qs}` : ''}`)
  },
  listMachines: () => request('/entries/machines'),
  listDays: () => request('/entries/days'),
  syncStatus: () => request('/entries/sync-status'),
  getEntry: (id) => request(`/entries/${id}`),
  createEntry: (payload) =>
    request('/entries', { method: 'POST', body: JSON.stringify(payload) }),
  updateEntry: (id, fields) =>
    request(`/entries/${id}`, { method: 'PATCH', body: JSON.stringify(fields) }),
  deleteEntry: (id, adminPassword) =>
    request(`/entries/${id}`, { method: 'DELETE', headers: adminHeader(adminPassword) }),

  listProjects: ({ category } = {}) => {
    const params = new URLSearchParams()
    if (category) params.set('category', category)
    const qs = params.toString()
    return request(`/projects${qs ? `?${qs}` : ''}`)
  },
  getProject: (id) => request(`/projects/${id}`),
  createProject: (payload) =>
    request('/projects', { method: 'POST', body: JSON.stringify(payload) }),
  updateProject: (id, fields) =>
    request(`/projects/${id}`, { method: 'PATCH', body: JSON.stringify(fields) }),

  listChecklist: ({ status, projectId } = {}) => {
    const params = new URLSearchParams()
    if (status) params.set('status', status)
    if (projectId) params.set('project_id', projectId)
    const qs = params.toString()
    return request(`/checklist${qs ? `?${qs}` : ''}`)
  },
  createChecklistItem: (payload) =>
    request('/checklist', { method: 'POST', body: JSON.stringify(payload) }),
  updateChecklistItem: (id, fields) =>
    request(`/checklist/${id}`, { method: 'PATCH', body: JSON.stringify(fields) }),

  onThisDay: (monthDay) => request(`/entries/on-this-day?month_day=${monthDay}`),
  remindersDue: () => request('/entries/reminders/due'),
  relatedEntries: ({ title, body, projectId, excludeId } = {}) => {
    const params = new URLSearchParams()
    if (title) params.set('title', title)
    if (body) params.set('body', body)
    if (projectId) params.set('project_id', projectId)
    if (excludeId) params.set('exclude_id', excludeId)
    return request(`/entries/related?${params.toString()}`)
  },

  uploadAttachment: (entryId, file) => {
    const form = new FormData()
    form.append('file', file)
    return fetch(`/api/entries/${entryId}/attachments`, {
      method: 'POST',
      credentials: 'include',
      body: form,
    }).then((r) => r.json())
  },
  listAttachments: (entryId) => request(`/entries/${entryId}/attachments`),
  attachmentUrl: (entryId, attachmentId) => `/api/entries/${entryId}/attachments/${attachmentId}/file`,

  listThreads: () => request('/threads'),
  createThread: (payload) => request('/threads', { method: 'POST', body: JSON.stringify(payload) }),
  getThread: (id) => request(`/threads/${id}`),
  addEntryToThread: (threadId, entryId) =>
    request(`/threads/${threadId}/entries/${entryId}`, { method: 'POST' }),

  aiStatus: () => request('/ai/status'),
  aiRecall: (question, day) =>
    request('/ai/recall', { method: 'POST', body: JSON.stringify({ question, day }) }),

  appSettings: () => request('/settings'),

  // tmux-archive terminal search/review
  terminalSearch: (q, projectId) => {
    const params = new URLSearchParams({ q })
    if (projectId) params.set('project_id', projectId)
    return request(`/terminal/search?${params.toString()}`)
  },
  listTerminalSessions: ({ projectId, limit } = {}) => {
    const params = new URLSearchParams()
    if (projectId) params.set('project_id', projectId)
    if (limit) params.set('limit', limit)
    const qs = params.toString()
    return request(`/terminal/sessions${qs ? `?${qs}` : ''}`)
  },
  getSessionChunks: (sessionId) => request(`/terminal/sessions/${sessionId}/chunks`),
  needsReviewList: () => request('/terminal/chunks/needs-review'),
  needsReviewCount: () => request('/terminal/chunks/needs-review/count'),
  approveChunk: (chunkId, text) =>
    request(`/terminal/chunks/${chunkId}/approve`, {
      method: 'PATCH',
      body: JSON.stringify(text != null ? { text } : {}),
    }),
  deleteTerminalSession: (id, adminPassword) =>
    request(`/terminal/sessions/${id}`, { method: 'DELETE', headers: adminHeader(adminPassword) }),

  // per-project cross-source timeline + AI handoff briefing
  projectTimeline: (projectId, { q, since, until } = {}) => {
    const params = new URLSearchParams()
    if (q) params.set('q', q)
    if (since) params.set('since', since)
    if (until) params.set('until', until)
    const qs = params.toString()
    return request(`/projects/${projectId}/timeline${qs ? `?${qs}` : ''}`)
  },
  projectHandoff: (projectId) => request(`/projects/${projectId}/handoff`),
}
