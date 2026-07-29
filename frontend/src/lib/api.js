async function request(path, options = {}) {
  const res = await fetch(`/api${path}`, {
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    ...options,
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
  listDays: () => request('/entries/days'),
  syncStatus: () => request('/entries/sync-status'),
  getEntry: (id) => request(`/entries/${id}`),
  createEntry: (payload) =>
    request('/entries', { method: 'POST', body: JSON.stringify(payload) }),
  updateEntry: (id, fields) =>
    request(`/entries/${id}`, { method: 'PATCH', body: JSON.stringify(fields) }),
  deleteEntry: (id) => request(`/entries/${id}`, { method: 'DELETE' }),

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
}
