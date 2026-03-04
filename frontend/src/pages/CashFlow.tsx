import { useEffect, useMemo, useState } from 'react'
import axios from 'axios'

type CashflowMode = 'current_assets' | 'sg' | 'cibc'
type CashflowFolder = 'inputs' | 'outputs'

interface CashflowFileEntry {
  key: string
  name: string
  folder: CashflowFolder
  size: number
  last_modified?: string | null
}

interface CashflowJobDefaults {
  mode: CashflowMode
  buy_num: string
  purchase_date: string
  target: number
  cprshock: number
  cdrshock: number
  workers: number
  current_assets_file?: string | null
  current_assets_output?: string | null
  prime_file?: string | null
  sfy_file?: string | null
  master_sheet?: string | null
  notes_sheet?: string | null
}

interface CashflowDefaultsResponse {
  bucket: string
  defaults: Record<CashflowMode, CashflowJobDefaults>
}

interface CashflowJobRequest {
  mode: CashflowMode
  buy_num: string
  purchase_date: string
  target: number
  cprshock: number
  cdrshock: number
  workers: number
  current_assets_file: string
  current_assets_output: string
  prime_file?: string | null
  sfy_file?: string | null
  master_sheet: string
  notes_sheet: string
}

interface CashflowJobResponse {
  job_id: string
  status: 'QUEUED' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'CANCELLED'
  mode: CashflowMode
  created_at: string
  started_at?: string | null
  completed_at?: string | null
  request: Record<string, unknown>
  output_files: CashflowFileEntry[]
  progress_percent: number
  progress_message?: string | null
  log_messages: string[]
  error_detail?: string | null
  cancel_requested: boolean
}

const modeLabels: Record<CashflowMode, string> = {
  current_assets: 'Current Assets',
  sg: 'SG',
  cibc: 'CIBC',
}

function fmtDate(value?: string | null) {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

function fmtSize(bytes: number) {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function buildInitialForm(mode: CashflowMode, defaults?: CashflowJobDefaults): CashflowJobRequest {
  const fallback: CashflowJobRequest = {
    mode,
    buy_num: '93rd',
    purchase_date: '2026-02-24',
    target: 7.9,
    cprshock: 1.0,
    cdrshock: 1.0,
    workers: 1,
    current_assets_file: 'current_assets.csv',
    current_assets_output: '',
    prime_file: mode === 'sg' ? '02-19-2026 Exhibit A To Form Of Sale Notice_sg.xlsx' : '02-19-2026 Exhibit A To Form Of Sale Notice_cibc.xlsx',
    sfy_file: mode === 'sg' ? 'FX3_02-19-2026_ExhibitAtoFormofSaleNotice_sg.xlsx' : 'FX3_02-19-2026_ExhibitAtoFormofSaleNotice_cibc.xlsx',
    master_sheet: 'MASTER_SHEET.xlsx',
    notes_sheet: 'MASTER_SHEET - Notes.xlsx',
  }
  const source = defaults ? { ...fallback, ...defaults } : fallback
  if (mode === 'current_assets') {
    return {
      ...source,
      mode,
      prime_file: null,
      sfy_file: null,
      current_assets_file: source.current_assets_file || 'current_assets.csv',
      current_assets_output: source.current_assets_output || '',
      master_sheet: source.master_sheet || 'MASTER_SHEET.xlsx',
      notes_sheet: source.notes_sheet || 'MASTER_SHEET - Notes.xlsx',
    }
  }
  return {
    ...source,
    mode,
    current_assets_file: 'current_assets.csv',
    current_assets_output: '',
    prime_file: source.prime_file || '',
    sfy_file: source.sfy_file || '',
    master_sheet: source.master_sheet || 'MASTER_SHEET.xlsx',
    notes_sheet: source.notes_sheet || 'MASTER_SHEET - Notes.xlsx',
  }
}

export default function CashFlow() {
  const [bucket, setBucket] = useState('intrepid-poc-qa')
  const [forms, setForms] = useState<Record<CashflowMode, CashflowJobRequest>>({
    current_assets: buildInitialForm('current_assets'),
    sg: buildInitialForm('sg'),
    cibc: buildInitialForm('cibc'),
  })
  const [jobs, setJobs] = useState<CashflowJobResponse[]>([])
  const [filesIn, setFilesIn] = useState<CashflowFileEntry[]>([])
  const [filesOut, setFilesOut] = useState<CashflowFileEntry[]>([])
  const [status, setStatus] = useState<string>('')
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  const selectedJob = useMemo(
    () => jobs.find((x) => x.job_id === selectedJobId) ?? null,
    [jobs, selectedJobId]
  )

  async function loadAll() {
    const [d, i, o, j] = await Promise.all([
      axios.get<CashflowDefaultsResponse>('/api/cashflow/defaults'),
      axios.get<CashflowFileEntry[]>('/api/cashflow/files/inputs'),
      axios.get<CashflowFileEntry[]>('/api/cashflow/files/outputs'),
      axios.get<CashflowJobResponse[]>('/api/cashflow/jobs'),
    ])
    setBucket(d.data.bucket)
    setForms({
      current_assets: buildInitialForm('current_assets', d.data.defaults.current_assets),
      sg: buildInitialForm('sg', d.data.defaults.sg),
      cibc: buildInitialForm('cibc', d.data.defaults.cibc),
    })
    setFilesIn(i.data)
    setFilesOut(o.data)
    setJobs(j.data)
    setSelectedJobId((prev) => prev && j.data.some((x) => x.job_id === prev) ? prev : (j.data[0]?.job_id ?? null))
  }

  useEffect(() => {
    loadAll().catch((err) => setStatus(err?.response?.data?.detail || err.message || 'Failed to load cashflow data'))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    const timer = setInterval(() => {
      axios.get<CashflowJobResponse[]>('/api/cashflow/jobs').then((r) => setJobs(r.data)).catch(() => {})
      axios.get<CashflowFileEntry[]>('/api/cashflow/files/outputs').then((r) => setFilesOut(r.data)).catch(() => {})
    }, 5000)
    return () => clearInterval(timer)
  }, [])

  function updateField(mode: CashflowMode, key: keyof CashflowJobRequest, value: string) {
    setForms((prev) => {
      const next = { ...prev }
      const item = { ...next[mode] }
      if (key === 'target' || key === 'cprshock' || key === 'cdrshock') item[key] = Number(value || 0) as never
      else if (key === 'workers') item.workers = Math.max(1, Number(value || 1))
      else item[key] = value as never
      next[mode] = item
      return next
    })
  }

  async function runMode(mode: CashflowMode) {
    setStatus('')
    try {
      const response = await axios.post<CashflowJobResponse>('/api/cashflow/jobs', forms[mode])
      setStatus(`Started ${modeLabels[mode]} job ${response.data.job_id}`)
      await loadAll()
    } catch (err: any) {
      setStatus(err?.response?.data?.detail || err.message || 'Failed to start cashflow job')
    }
  }

  async function cancelJob(jobId: string) {
    try {
      await axios.post(`/api/cashflow/jobs/${jobId}/cancel`)
      setStatus(`Cancellation requested for ${jobId}`)
      await loadAll()
    } catch (err: any) {
      setStatus(err?.response?.data?.detail || err.message || 'Failed to cancel job')
    }
  }

  async function uploadInput(files: FileList | null) {
    if (!files || files.length === 0) return
    setStatus('')
    try {
      for (const file of Array.from(files)) {
        const formData = new FormData()
        formData.append('file', file)
        await axios.post('/api/cashflow/files/inputs', formData, {
          headers: { 'Content-Type': 'multipart/form-data' },
        })
      }
      setStatus(`Uploaded ${files.length} file(s)`)
      await loadAll()
    } catch (err: any) {
      setStatus(err?.response?.data?.detail || err.message || 'Upload failed')
    }
  }

  async function downloadFile(file: CashflowFileEntry) {
    const response = await axios.get(
      `/api/cashflow/files/${file.folder}/download`,
      { params: { key: file.key }, responseType: 'blob' }
    )
    const blobUrl = window.URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = blobUrl
    link.download = file.name
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.URL.revokeObjectURL(blobUrl)
  }

  if (loading) return <div className="text-center py-8">Loading cashflow...</div>

  return (
    <div className="px-4 py-6 sm:px-0 space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-2xl font-bold text-gray-900">Cash Flow</h1>
        <button onClick={() => loadAll()} className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700">
          Refresh
        </button>
      </div>

      <div className="bg-blue-50 border border-blue-200 rounded-md p-4 text-sm">
        <div className="font-medium">Storage Bucket</div>
        <div>{bucket}</div>
      </div>

      {status && <div className="bg-gray-100 border border-gray-300 rounded-md p-3 text-sm">{status}</div>}

      <div className="bg-white shadow rounded-lg p-4">
        <h2 className="text-lg font-semibold mb-3">Files</h2>
        <div className="mb-4">
          <input type="file" multiple onChange={(e) => uploadInput(e.target.files)} />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <div>
            <h3 className="font-medium mb-2">Inputs ({filesIn.length})</h3>
            <div className="space-y-2">
              {filesIn.map((f) => (
                <div key={f.key} className="flex justify-between text-sm border rounded p-2">
                  <span className="truncate pr-3">{f.name}</span>
                  <button className="text-blue-600" onClick={() => downloadFile(f)}>Download</button>
                </div>
              ))}
            </div>
          </div>
          <div>
            <h3 className="font-medium mb-2">Outputs ({filesOut.length})</h3>
            <div className="space-y-2">
              {filesOut.map((f) => (
                <div key={f.key} className="flex justify-between text-sm border rounded p-2">
                  <span className="truncate pr-3">{f.name} ({fmtSize(f.size)})</span>
                  <button className="text-blue-600" onClick={() => downloadFile(f)}>Download</button>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        {(['current_assets', 'sg', 'cibc'] as CashflowMode[]).map((mode) => (
          <div key={mode} className="bg-white shadow rounded-lg p-4 space-y-3">
            <h2 className="text-lg font-semibold">{modeLabels[mode]}</h2>
            <div className="grid grid-cols-1 gap-2">
              <input className="border rounded px-3 py-2 text-sm" value={forms[mode].buy_num} onChange={(e) => updateField(mode, 'buy_num', e.target.value)} placeholder="Buy Num" />
              <input className="border rounded px-3 py-2 text-sm" type="date" value={forms[mode].purchase_date} onChange={(e) => updateField(mode, 'purchase_date', e.target.value)} />
              <input className="border rounded px-3 py-2 text-sm" type="number" step="0.1" value={forms[mode].target} onChange={(e) => updateField(mode, 'target', e.target.value)} placeholder="Target" />
              <input className="border rounded px-3 py-2 text-sm" type="number" step="0.01" value={forms[mode].cprshock} onChange={(e) => updateField(mode, 'cprshock', e.target.value)} placeholder="CPR Shock" />
              <input className="border rounded px-3 py-2 text-sm" type="number" step="0.01" value={forms[mode].cdrshock} onChange={(e) => updateField(mode, 'cdrshock', e.target.value)} placeholder="CDR Shock" />
              {mode === 'current_assets' ? (
                <>
                  <input className="border rounded px-3 py-2 text-sm" value={forms[mode].current_assets_file} onChange={(e) => updateField(mode, 'current_assets_file', e.target.value)} placeholder="Input CSV" />
                  <input className="border rounded px-3 py-2 text-sm" value={forms[mode].current_assets_output} onChange={(e) => updateField(mode, 'current_assets_output', e.target.value)} placeholder="Output file name" />
                  <input className="border rounded px-3 py-2 text-sm" type="number" min="1" value={forms[mode].workers} onChange={(e) => updateField(mode, 'workers', e.target.value)} placeholder="Workers" />
                </>
              ) : (
                <>
                  <input className="border rounded px-3 py-2 text-sm" value={forms[mode].prime_file || ''} onChange={(e) => updateField(mode, 'prime_file', e.target.value)} placeholder="Prime workbook" />
                  <input className="border rounded px-3 py-2 text-sm" value={forms[mode].sfy_file || ''} onChange={(e) => updateField(mode, 'sfy_file', e.target.value)} placeholder="SFY workbook" />
                </>
              )}
            </div>
            <button onClick={() => runMode(mode)} className="w-full px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700">
              Run {modeLabels[mode]}
            </button>
          </div>
        ))}
      </div>

      <div className="bg-white shadow rounded-lg p-4">
        <h2 className="text-lg font-semibold mb-3">Run History</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Mode</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Started</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Completed</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Progress</th>
                <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {jobs.map((job) => (
                <tr key={job.job_id} className={selectedJobId === job.job_id ? 'bg-blue-50' : ''} onClick={() => setSelectedJobId(job.job_id)}>
                  <td className="px-4 py-2 text-sm">{modeLabels[job.mode]}</td>
                  <td className="px-4 py-2 text-sm">{job.status}</td>
                  <td className="px-4 py-2 text-sm">{fmtDate(job.started_at)}</td>
                  <td className="px-4 py-2 text-sm">{fmtDate(job.completed_at)}</td>
                  <td className="px-4 py-2 text-sm">{job.progress_percent}% {job.progress_message || ''}</td>
                  <td className="px-4 py-2 text-sm">
                    {(job.status === 'QUEUED' || job.status === 'RUNNING') && (
                      <button className="text-red-600" onClick={(e) => { e.stopPropagation(); cancelJob(job.job_id) }}>
                        Cancel
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {selectedJob && (
          <div className="mt-4 border-t pt-3">
            <div className="text-sm font-medium mb-2">Job {selectedJob.job_id}</div>
            {selectedJob.error_detail && <div className="text-sm text-red-700 mb-2">{selectedJob.error_detail}</div>}
            <div className="text-xs bg-gray-900 text-gray-100 rounded p-3 max-h-64 overflow-y-auto space-y-1">
              {selectedJob.log_messages.length === 0 ? <div>No log lines yet.</div> : selectedJob.log_messages.map((line, idx) => <div key={idx}>{line}</div>)}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
