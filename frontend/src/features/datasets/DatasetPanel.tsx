import {
	AlertTriangle,
	CheckCircle2,
	ClipboardPaste,
	CloudUpload,
	Loader2,
	Trash2,
	XCircle,
} from "lucide-react";
import { type ChangeEvent, useRef, useState } from "react";

import { Button } from "#/components/ui/button";
import { Modal } from "#/components/ui/modal";
import { Spinner } from "#/components/ui/spinner";
import { readErrorMessage } from "#/lib/api";

import { listWorkbookSheets } from "./api";
import {
	useDataset,
	useDatasets,
	useDeleteDataset,
	useUploadDataset,
} from "./hooks";
import { PasteDialog } from "./PasteDialog";
import { PreviewTable } from "./PreviewTable";
import {
	DATASET_COLUMN_NOTES,
	DATASET_KIND_DESCRIPTIONS,
	DATASET_KIND_LABELS,
	DATASET_REQUIRED_COLUMNS,
	type Dataset,
	type DatasetKind,
} from "./types";
import { ValidationErrorsPanel } from "./ValidationErrorsPanel";

type Props = {
	projectId: number;
	kind: DatasetKind;
};

export function DatasetPanel({ projectId, kind }: Props) {
	const datasetsQuery = useDatasets(projectId, kind);
	const upload = useUploadDataset(projectId);
	const remove = useDeleteDataset(projectId);
	const fileRef = useRef<HTMLInputElement>(null);

	const [pasteOpen, setPasteOpen] = useState(false);
	const [sheetModalOpen, setSheetModalOpen] = useState(false);
	const [sheetOptions, setSheetOptions] = useState<string[]>([]);
	const [selectedSheet, setSelectedSheet] = useState("");
	const [pendingExcelFile, setPendingExcelFile] = useState<File | null>(null);
	const [inspectingWorkbook, setInspectingWorkbook] = useState(false);
	const [selectedId, setSelectedId] = useState<number | null>(null);
	const [actionError, setActionError] = useState<string | null>(null);

	const datasets = datasetsQuery.data ?? [];
	const activeId = selectedId ?? datasets[0]?.id ?? null;
	const detailQuery = useDataset(projectId, activeId ?? undefined);

	async function onFile(event: ChangeEvent<HTMLInputElement>) {
		const file = event.target.files?.[0];
		if (!file) return;
		setActionError(null);
		try {
			if (isExcelFile(file)) {
				setInspectingWorkbook(true);
				const sheets = await listWorkbookSheets(projectId, file);
				if (sheets.length > 1) {
					setPendingExcelFile(file);
					setSheetOptions(sheets);
					setSelectedSheet(sheets[0]);
					setSheetModalOpen(true);
					return;
				}
				await upload.mutateAsync({ file, kind, sheetName: sheets[0] });
				return;
			}
			await upload.mutateAsync({ file, kind });
		} catch (err) {
			setActionError(await readErrorMessage(err));
		} finally {
			setInspectingWorkbook(false);
			if (fileRef.current) fileRef.current.value = "";
		}
	}

	async function uploadSelectedSheet() {
		if (!pendingExcelFile || !selectedSheet) return;
		setActionError(null);
		try {
			await upload.mutateAsync({
				file: pendingExcelFile,
				kind,
				sheetName: selectedSheet,
			});
			setSheetModalOpen(false);
			setPendingExcelFile(null);
			setSheetOptions([]);
			setSelectedSheet("");
		} catch (err) {
			setActionError(await readErrorMessage(err));
		}
	}

	async function onDelete(dataset: Dataset) {
		if (!confirm(`Delete this ${DATASET_KIND_LABELS[kind]} dataset?`)) return;
		setActionError(null);
		try {
			await remove.mutateAsync(dataset.id);
			if (selectedId === dataset.id) setSelectedId(null);
		} catch (err) {
			setActionError(await readErrorMessage(err));
		}
	}

	return (
		<div className="space-y-5">
			<header className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
				<div>
					<h2 className="display-title text-xl font-bold text-(--sea-ink)">
						{DATASET_KIND_LABELS[kind]} data
					</h2>
					<p className="mt-1 max-w-2xl text-sm text-(--sea-ink-soft)">
						{DATASET_KIND_DESCRIPTIONS[kind]}
					</p>
				</div>
				<div className="flex flex-wrap items-center gap-2">
					<Button variant="secondary" onClick={() => setPasteOpen(true)}>
						<ClipboardPaste size={16} />
						Paste
					</Button>
					<Button
						onClick={() => fileRef.current?.click()}
						isLoading={upload.isPending || inspectingWorkbook}
					>
						<CloudUpload size={16} />
						Upload file
					</Button>
					<input
						ref={fileRef}
						type="file"
						accept=".csv,.tsv,.txt,.xlsx,.xls"
						className="hidden"
						onChange={onFile}
					/>
				</div>
			</header>

			{actionError ? (
				<div
					role="alert"
					className="rounded-xl border border-red-200/70 bg-red-50/80 px-3 py-2 text-sm text-red-700"
				>
					{actionError}
				</div>
			) : null}

			<ColumnFormatCaution kind={kind} />

			{datasetsQuery.isPending ? (
				<div className="flex items-center gap-2 text-sm text-(--sea-ink-soft)">
					<Spinner size="sm" />
					Loading datasets…
				</div>
			) : datasets.length === 0 ? (
				<EmptyState
					onPaste={() => setPasteOpen(true)}
					onUpload={() => fileRef.current?.click()}
					kind={kind}
				/>
			) : (
				<div className="space-y-4">
					<DatasetList
						datasets={datasets}
						activeId={activeId}
						onSelect={setSelectedId}
						onDelete={onDelete}
						deletingId={
							remove.isPending
								? ((remove.variables as number | undefined) ?? null)
								: null
						}
					/>

					{detailQuery.isPending ? (
						<div className="flex items-center gap-2 text-sm text-(--sea-ink-soft)">
							<Loader2 className="animate-spin" size={16} /> Loading details…
						</div>
					) : detailQuery.data ? (
						<>
							<ValidationErrorsPanel
								errors={detailQuery.data.validation_errors}
								totalRows={detailQuery.data.row_count}
							/>
							<div>
								<h3 className="mb-2 text-sm font-semibold text-(--sea-ink-soft)">
									Preview
								</h3>
								<PreviewTable rows={detailQuery.data.raw_data ?? []} />
							</div>
						</>
					) : null}
				</div>
			)}

			<PasteDialog
				open={pasteOpen}
				onClose={() => setPasteOpen(false)}
				projectId={projectId}
				kind={kind}
			/>
			<Modal
				open={sheetModalOpen}
				onClose={() => {
					setSheetModalOpen(false);
					setPendingExcelFile(null);
				}}
				title="Choose Excel sheet"
				description="This workbook has multiple sheets. Pick the sheet to validate and save."
				footer={
					<>
						<Button
							variant="ghost"
							onClick={() => {
								setSheetModalOpen(false);
								setPendingExcelFile(null);
							}}
						>
							Cancel
						</Button>
						<Button onClick={uploadSelectedSheet} isLoading={upload.isPending}>
							Upload selected sheet
						</Button>
					</>
				}
			>
				<div className="space-y-2">
					{sheetOptions.map((sheet) => (
						<label
							key={sheet}
							className="flex cursor-pointer items-center gap-3 rounded-xl border border-(--line) bg-(--surface)/60 px-3 py-2 text-sm text-(--sea-ink) hover:bg-(--surface-strong)"
						>
							<input
								type="radio"
								name="excel-sheet"
								value={sheet}
								checked={selectedSheet === sheet}
								onChange={() => setSelectedSheet(sheet)}
							/>
							<span>{sheet}</span>
						</label>
					))}
				</div>
			</Modal>
		</div>
	);
}

function ColumnFormatCaution({ kind }: { kind: DatasetKind }) {
	return (
		<div className="rounded-2xl border border-amber-200/80 bg-amber-50/80 p-4 text-sm text-amber-900">
			<div className="flex items-start gap-3">
				<AlertTriangle size={18} className="mt-0.5 shrink-0 text-amber-600" />
				<div>
					<p className="font-semibold">Required column format</p>
					<div className="mt-2 flex flex-wrap gap-2">
						{DATASET_REQUIRED_COLUMNS[kind].map((col) => (
							<code
								key={col}
								className="rounded-lg border border-amber-200 bg-white/70 px-2 py-1 text-xs text-amber-900"
							>
								{col}
							</code>
						))}
					</div>
					<p className="mt-2 text-xs leading-relaxed text-amber-800">
						{DATASET_COLUMN_NOTES[kind]}
					</p>
				</div>
			</div>
		</div>
	);
}

function isExcelFile(file: File): boolean {
	const name = file.name.toLowerCase();
	return name.endsWith(".xlsx") || name.endsWith(".xls");
}

function DatasetList({
	datasets,
	activeId,
	onSelect,
	onDelete,
	deletingId,
}: {
	datasets: Dataset[];
	activeId: number | null;
	onSelect: (id: number) => void;
	onDelete: (dataset: Dataset) => void;
	deletingId: number | null;
}) {
	return (
		<div className="overflow-hidden rounded-2xl border border-(--line) bg-(--surface-strong)">
			<table className="min-w-full text-sm">
				<thead className="bg-(--surface)">
					<tr>
						<th className="px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wider text-(--sea-ink-soft)">
							Source
						</th>
						<th className="px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wider text-(--sea-ink-soft)">
							Rows
						</th>
						<th className="px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wider text-(--sea-ink-soft)">
							Status
						</th>
						<th className="px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wider text-(--sea-ink-soft)">
							Created
						</th>
						<th className="px-3 py-2 text-right" />
					</tr>
				</thead>
				<tbody>
					{datasets.map((ds, idx) => {
						const active = ds.id === activeId;
						return (
							<tr
								key={ds.id}
								className={
									active
										? "bg-(--lagoon)/12"
										: idx % 2 === 0
											? "bg-(--surface-strong)"
											: "bg-(--surface)"
								}
							>
								<td className="px-3 py-2 align-top">
									<button
										type="button"
										onClick={() => onSelect(ds.id)}
										className="flex flex-col items-start gap-0.5 text-left"
									>
										<span className="font-semibold text-(--sea-ink)">
											{ds.filename ?? `Pasted ${ds.source}`}
										</span>
										<span className="text-xs uppercase tracking-wider text-(--sea-ink-soft)">
											{ds.source}
										</span>
									</button>
								</td>
								<td className="px-3 py-2 align-top text-(--sea-ink)">
									{ds.row_count}
								</td>
								<td className="px-3 py-2 align-top">
									{ds.is_valid ? (
										<span className="inline-flex items-center gap-1 rounded-full bg-(--palm)/12 px-2 py-0.5 text-xs font-semibold text-(--palm)">
											<CheckCircle2 size={12} />
											Valid
										</span>
									) : (
										<span className="inline-flex items-center gap-1 rounded-full bg-red-100 px-2 py-0.5 text-xs font-semibold text-red-700">
											<XCircle size={12} />
											{ds.validation_errors?.length ?? 0} issue
											{(ds.validation_errors?.length ?? 0) === 1 ? "" : "s"}
										</span>
									)}
								</td>
								<td className="px-3 py-2 align-top text-xs text-(--sea-ink-soft)">
									{new Date(ds.created_at).toLocaleString()}
								</td>
								<td className="px-3 py-2 align-top text-right">
									<button
										type="button"
										onClick={() => onDelete(ds)}
										disabled={deletingId === ds.id}
										aria-label="Delete dataset"
										className="grid h-8 w-8 place-items-center rounded-full text-(--sea-ink-soft) transition-colors hover:bg-red-50 hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-50"
									>
										{deletingId === ds.id ? (
											<Spinner size="sm" />
										) : (
											<Trash2 size={14} />
										)}
									</button>
								</td>
							</tr>
						);
					})}
				</tbody>
			</table>
		</div>
	);
}

function EmptyState({
	onPaste,
	onUpload,
	kind,
}: {
	onPaste: () => void;
	onUpload: () => void;
	kind: DatasetKind;
}) {
	return (
		<div className="island-shell rounded-3xl p-8 text-center">
			<h3 className="display-title text-lg font-bold text-(--sea-ink)">
				No {DATASET_KIND_LABELS[kind]} data yet
			</h3>
			<p className="mx-auto mt-2 max-w-md text-sm text-(--sea-ink-soft)">
				Paste a TSV/CSV from your spreadsheet, or upload a CSV/XLSX file. Each
				upload is validated row-by-row before being saved.
			</p>
			<div className="mt-5 flex flex-wrap justify-center gap-2">
				<Button variant="secondary" onClick={onPaste}>
					<ClipboardPaste size={16} />
					Paste from clipboard
				</Button>
				<Button onClick={onUpload}>
					<CloudUpload size={16} />
					Upload file
				</Button>
			</div>
		</div>
	);
}
