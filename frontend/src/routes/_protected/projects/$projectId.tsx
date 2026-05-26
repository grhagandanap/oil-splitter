import { createFileRoute, useNavigate } from '@tanstack/react-router'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useRef, useState } from 'react'
import * as XLSX from 'xlsx'
import { projectsApi, type FileType, type ExecutionHistoryResponse } from '#/lib/api'
import { getToken } from '#/lib/api'
import { Button } from '#/components/ui/button'
import { Card, CardHeader, CardTitle, CardDescription } from '#/components/ui/card'

export const Route = createFileRoute('/_protected/projects/$projectId')({
  component: ProjectDetailPage,
})

const FILE_SLOTS: { type: FileType; label: string; hint: string }[] = [
  { type: 'marker',     label: 'Marker Data',      hint: 'Columns: Well, Surface, MD' },
  { type: 'well',       label: 'Sand/Zone List',    hint: 'Column: Marker (ordered zone names)' },
  { type: 'production', label: 'Production Data',   hint: 'Columns: WELL, DATE, OIL, WATER, GAS, WINJ' },
  { type: 'completion', label: 'Completion Data',   hint: 'Columns: WELL, DATE, Perf Status, Perf Top, Perf Base' },
  { type: 'lumping',    label: 'Lumping / kh Data', hint: 'Columns: Well, Zone, Lumping (kh weight)' },
]

const STATUS_COLOR: Record<string, string> = {
  pending:    'bg-yellow-100 text-yellow-800',
  processing: 'bg-blue-100 text-blue-800',
  completed:  'bg-green-100 text-green-800',
  failed:     'bg-red-100 text-red-800',
}

function ProjectDetailPage() {
  const { projectId } = Route.useParams()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data: project, isLoading } = useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projectsApi.get(projectId),
  })

  const isProcessing = project?.status === 'processing'

  const { data: history = [] } = useQuery({
    queryKey: ['history', projectId],
    queryFn: () => projectsApi.getHistory(projectId),
    refetchInterval: isProcessing ? 2000 : false,
    refetchIntervalInBackground: false,
  })

  const uploadMutation = useMutation({
    mutationFn: ({ fileType, file, sheetName }: { fileType: FileType; file: File; sheetName?: string }) =>
      projectsApi.uploadFile(projectId, fileType, file, sheetName),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['project', projectId] }),
  })

  const executeMutation = useMutation({
    mutationFn: () => projectsApi.execute(projectId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['project', projectId] })
      qc.invalidateQueries({ queryKey: ['history', projectId] })
    },
  })

  const uploadedTypes = new Set(project?.files.map((f) => f.file_type) ?? [])
  const allUploaded = FILE_SLOTS.every((s) => uploadedTypes.has(s.type))

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64 text-[var(--sea-ink-soft)]">
        Loading…
      </div>
    )
  }

  if (!project) return null

  return (
    <div className="px-8 py-8 max-w-5xl mx-auto">
      <div className="flex items-center gap-3 mb-6">
        <button
          onClick={() => navigate({ to: '/dashboard' })}
          className="text-[var(--sea-ink-soft)] hover:text-[var(--sea-ink)] transition-colors"
        >
          ← Dashboard
        </button>
        <span className="text-[var(--line)]">/</span>
        <h2 className="text-xl font-bold text-[var(--sea-ink)]">{project.name}</h2>
        <span
          className={`ml-auto text-xs font-medium px-2.5 py-1 rounded-full ${STATUS_COLOR[project.status] ?? 'bg-gray-100 text-gray-700'}`}
        >
          {project.status}
        </span>
      </div>

      {project.description && (
        <p className="text-sm text-[var(--sea-ink-soft)] mb-6">{project.description}</p>
      )}

      <h3 className="text-sm font-semibold text-[var(--sea-ink)] mb-4">
        Dataset Files
        <span className="ml-2 text-xs font-normal text-[var(--sea-ink-soft)]">
          ({uploadedTypes.size} / {FILE_SLOTS.length} uploaded)
        </span>
      </h3>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 mb-8">
        {FILE_SLOTS.map((slot) => (
          <FileUploadCard
            key={slot.type}
            slot={slot}
            uploadedFile={project.files.find((f) => f.file_type === slot.type)}
            isUploading={
              uploadMutation.isPending &&
              (uploadMutation.variables as any)?.fileType === slot.type
            }
            onUpload={(file, sheetName) => uploadMutation.mutate({ fileType: slot.type, file, sheetName })}
          />
        ))}
      </div>

      <div className="island-shell border border-[var(--line)] rounded-2xl p-6 mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-semibold text-[var(--sea-ink)]">Run Engine</h3>
            <p className="text-sm text-[var(--sea-ink-soft)] mt-0.5">
              {allUploaded
                ? 'All files ready. Execute the full marker → squeeze → split pipeline.'
                : `Upload all ${FILE_SLOTS.length} files to enable execution.`}
            </p>
          </div>
          <Button
            disabled={!allUploaded || executeMutation.isPending || isProcessing}
            onClick={() => executeMutation.mutate()}
            className="bg-gradient-to-r from-[var(--lagoon)] to-[var(--palm)] text-white border-0 hover:opacity-90 disabled:opacity-40"
          >
            {isProcessing ? (
              <>
                <SpinnerIcon className="size-4 mr-2 animate-spin" />
                Processing…
              </>
            ) : (
              'Execute'
            )}
          </Button>
        </div>
        {executeMutation.isError && (
          <p className="mt-3 text-sm text-red-600">
            {(executeMutation.error as Error).message}
          </p>
        )}
      </div>

      {history.length > 0 && (
        <div>
          <h3 className="text-sm font-semibold text-[var(--sea-ink)] mb-3">Execution History</h3>
          <div className="space-y-3">
            {history.map((h) => (
              <HistoryRow key={h.id} execution={h} projectId={projectId} />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

async function readSheetNames(file: File): Promise<string[]> {
  const ext = file.name.split('.').pop()?.toLowerCase()
  if (ext !== 'xlsx' && ext !== 'xls') return []
  const buf = await file.arrayBuffer()
  const wb = XLSX.read(buf, { bookSheets: true })
  return wb.SheetNames
}

function FileUploadCard({
  slot,
  uploadedFile,
  isUploading,
  onUpload,
}: {
  slot: (typeof FILE_SLOTS)[0]
  uploadedFile?: { original_filename: string; sheet_name: string | null; uploaded_at: string }
  isUploading: boolean
  onUpload: (file: File, sheetName?: string) => void
}) {
  const inputRef = useRef<HTMLInputElement>(null)
  const [pendingFile, setPendingFile] = useState<File | null>(null)
  const [sheets, setSheets] = useState<string[]>([])
  const [isReading, setIsReading] = useState(false)

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0]
    e.target.value = ''
    if (!f) return

    setIsReading(true)
    const names = await readSheetNames(f)
    setIsReading(false)

    if (names.length <= 1) {
      onUpload(f, names[0])
    } else {
      setPendingFile(f)
      setSheets(names)
    }
  }

  const handleSheetPick = (sheetName: string) => {
    if (pendingFile) onUpload(pendingFile, sheetName)
    setPendingFile(null)
    setSheets([])
  }

  const handleCancel = () => {
    setPendingFile(null)
    setSheets([])
  }

  return (
    <Card className="island-shell border-[var(--line)] gap-2">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <CardTitle className="text-sm font-semibold text-[var(--sea-ink)]">
              {slot.label}
            </CardTitle>
            <CardDescription className="text-xs mt-0.5 leading-snug">{slot.hint}</CardDescription>
          </div>
          {uploadedFile ? (
            <span className="shrink-0 inline-flex items-center gap-1 text-xs text-green-700 bg-green-50 px-2 py-0.5 rounded-full">
              <svg className="size-3" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
              </svg>
              Done
            </span>
          ) : (
            <span className="shrink-0 text-xs text-[var(--sea-ink-soft)] bg-[var(--sand)] px-2 py-0.5 rounded-full">
              Needed
            </span>
          )}
        </div>

        {uploadedFile && (
          <div className="mt-1">
            <p className="text-xs text-[var(--sea-ink-soft)] truncate">{uploadedFile.original_filename}</p>
            {uploadedFile.sheet_name && (
              <p className="text-xs text-[var(--lagoon)] mt-0.5">Sheet: {uploadedFile.sheet_name}</p>
            )}
          </div>
        )}

        {sheets.length > 1 && pendingFile ? (
          <div className="mt-2">
            <p className="text-xs font-medium text-[var(--sea-ink)] mb-1.5">
              Select sheet from <span className="font-semibold">{pendingFile.name}</span>:
            </p>
            <div className="flex flex-col gap-1">
              {sheets.map((name) => (
                <button
                  key={name}
                  onClick={() => handleSheetPick(name)}
                  className="text-left text-xs px-3 py-1.5 rounded-lg border border-[var(--line)] hover:border-[var(--lagoon)] hover:bg-[var(--lagoon)]/5 transition-colors text-[var(--sea-ink)] truncate"
                >
                  {name}
                </button>
              ))}
            </div>
            <button
              onClick={handleCancel}
              className="mt-1.5 text-xs text-[var(--sea-ink-soft)] hover:text-[var(--sea-ink)] underline"
            >
              Cancel
            </button>
          </div>
        ) : (
          <>
            <input
              ref={inputRef}
              type="file"
              accept=".csv,.xlsx,.xls"
              className="hidden"
              onChange={handleFileChange}
            />
            <Button
              size="sm"
              variant="outline"
              disabled={isUploading || isReading}
              onClick={() => inputRef.current?.click()}
              className="w-full mt-2 text-xs h-8"
            >
              {isUploading ? 'Uploading…' : isReading ? 'Reading…' : uploadedFile ? 'Replace File' : 'Upload File'}
            </Button>
          </>
        )}
      </CardHeader>
    </Card>
  )
}

function HistoryRow({
  execution,
  projectId,
}: {
  execution: ExecutionHistoryResponse
  projectId: string
}) {
  const [showLogs, setShowLogs] = useState(false)
  const token = getToken()

  const downloadUrl = projectsApi.downloadResult(projectId, execution.id)

  return (
    <div className="island-shell border border-[var(--line)] rounded-xl p-4">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-3">
          <span
            className={`text-xs font-medium px-2.5 py-0.5 rounded-full ${STATUS_COLOR[execution.status] ?? 'bg-gray-100 text-gray-700'}`}
          >
            {execution.status}
          </span>
          <span className="text-xs text-[var(--sea-ink-soft)]">
            {new Date(execution.executed_at).toLocaleString()}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {execution.logs && (
            <button
              onClick={() => setShowLogs((v) => !v)}
              className="text-xs text-[var(--lagoon)] hover:underline"
            >
              {showLogs ? 'Hide logs' : 'View logs'}
            </button>
          )}
          {execution.status === 'completed' && (
            <a
              href={`${downloadUrl}?token=${token}`}
              download
              className="text-xs px-3 py-1 rounded-lg bg-[var(--lagoon)] text-white hover:opacity-80 transition-opacity"
            >
              Download
            </a>
          )}
        </div>
      </div>
      {showLogs && execution.logs && (
        <pre className="mt-3 text-xs bg-[var(--sand)] rounded-lg p-3 overflow-x-auto text-[var(--sea-ink)] whitespace-pre-wrap max-h-48 overflow-y-auto">
          {execution.logs}
        </pre>
      )}
    </div>
  )
}

function SpinnerIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  )
}
