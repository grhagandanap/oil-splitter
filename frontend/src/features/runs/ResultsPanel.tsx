import {
	AlertTriangle,
	CheckCircle2,
	CircleDot,
	Download,
	History,
	Play,
	Table2,
	XCircle,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";

import { Button } from "#/components/ui/button";
import { Spinner } from "#/components/ui/spinner";
import { type TabItem, Tabs } from "#/components/ui/tabs";
import { readErrorMessage } from "#/lib/api";

import { downloadRunExport } from "./api";
import { useRun, useRuns, useStartRun } from "./hooks";
import { ResultsTable } from "./ResultsTable";
import type { ExportFormat, RunTable, SplitRun } from "./types";

/** Top level: markered production with ``p`` vs KH split output. */
type MainViewTab = "marker" | "split";

const MAIN_TABS: TabItem<MainViewTab>[] = [
	{
		value: "marker",
		label: "Perforation marker",
		icon: <CircleDot size={14} />,
	},
	{ value: "split", label: "Split result", icon: <Table2 size={14} /> },
];

type SplitSubTab = "summary" | "detail";

const SPLIT_TABS: TabItem<SplitSubTab>[] = [
	{ value: "summary", label: "Summary (per sand)" },
	{ value: "detail", label: "Detail (per row)" },
];

type Props = {
	projectId: number;
};

export function ResultsPanel({ projectId }: Props) {
	const runsQuery = useRuns(projectId);
	const startRun = useStartRun(projectId);

	const [selectedRunId, setSelectedRunId] = useState<number | null>(null);
	const [mainTab, setMainTab] = useState<MainViewTab>("marker");
	const [splitSubTab, setSplitSubTab] = useState<SplitSubTab>("summary");
	const [actionError, setActionError] = useState<string | null>(null);
	const [exporting, setExporting] = useState<{
		table: RunTable;
		format: ExportFormat;
	} | null>(null);

	const runs = runsQuery.data ?? [];
	const activeRunId = selectedRunId ?? runs[0]?.id ?? null;

	// When a new run completes, jump to it.
	useEffect(() => {
		const last = startRun.data;
		if (last) setSelectedRunId(last.id);
	}, [startRun.data]);

	const detailQuery = useRun(projectId, activeRunId ?? undefined);

	async function onRun() {
		setActionError(null);
		try {
			await startRun.mutateAsync();
		} catch (err) {
			setActionError(await readErrorMessage(err));
		}
	}

	async function onExport(table: RunTable, format: ExportFormat) {
		if (!activeRunId) return;
		setActionError(null);
		setExporting({ table, format });
		try {
			await downloadRunExport(projectId, activeRunId, { table, format });
		} catch (err) {
			setActionError(await readErrorMessage(err));
		} finally {
			setExporting(null);
		}
	}

	const activeRun = detailQuery.data;
	const markerRows = useMemo(
		() => activeRun?.marker_preview ?? [],
		[activeRun?.marker_preview],
	);
	const summaryRows = useMemo(
		() => activeRun?.summary ?? [],
		[activeRun?.summary],
	);
	const detailRows = useMemo(
		() => activeRun?.detail ?? [],
		[activeRun?.detail],
	);

	const exportTable: RunTable = useMemo(
		() =>
			mainTab === "marker"
				? "marker"
				: splitSubTab === "summary"
					? "summary"
					: "detail",
		[mainTab, splitSubTab],
	);

	return (
		<div className="space-y-6">
			<div className="flex flex-wrap items-center justify-between gap-4">
				<div>
					<h2 className="display-title text-xl font-bold text-(--sea-ink)">
						Splitter results
					</h2>
					<p className="mt-1 text-sm text-(--sea-ink-soft)">
						Run the KH-weighted splitter against the latest valid datasets for
						this project. Past runs stay listed below.
					</p>
				</div>
				<Button
					onClick={onRun}
					isLoading={startRun.isPending}
					className="shrink-0"
				>
					<Play size={16} />
					{startRun.isPending ? "Running splitter…" : "Run splitter"}
				</Button>
			</div>

			{actionError ? (
				<div className="rounded-2xl border border-red-200 bg-red-50/80 px-4 py-3 text-sm text-red-700">
					{actionError}
				</div>
			) : null}

			{runs.length > 0 ? (
				<RunsHistory
					runs={runs}
					activeId={activeRunId}
					onSelect={(id) => setSelectedRunId(id)}
				/>
			) : runsQuery.isPending ? (
				<div className="flex items-center gap-2 text-sm text-(--sea-ink-soft)">
					<Spinner size="sm" />
					Loading runs…
				</div>
			) : null}

			{activeRunId === null ? (
				<EmptyState />
			) : detailQuery.isPending ? (
				<div className="flex items-center gap-2 text-sm text-(--sea-ink-soft)">
					<Spinner size="sm" />
					Loading run…
				</div>
			) : !activeRun ? null : activeRun.status === "failed" ? (
				<RunFailed run={activeRun} />
			) : (
				<div className="space-y-4">
					<RunMeta run={activeRun} />
					{(activeRun.warnings ?? []).length > 0 ? (
						<WarningsBlock warnings={activeRun.warnings ?? []} />
					) : null}

					<div className="flex flex-wrap items-center justify-between gap-3 border-b border-(--line)/70 pb-1">
						<Tabs items={MAIN_TABS} value={mainTab} onChange={setMainTab} />
						<div className="flex flex-wrap items-center gap-2">
							<Button
								size="sm"
								variant="secondary"
								onClick={() => onExport(exportTable, "csv")}
								isLoading={
									exporting?.table === exportTable && exporting.format === "csv"
								}
							>
								<Download size={14} />
								Export CSV
							</Button>
							<Button
								size="sm"
								variant="secondary"
								onClick={() => onExport(exportTable, "xlsx")}
								isLoading={
									exporting?.table === exportTable &&
									exporting.format === "xlsx"
								}
							>
								<Download size={14} />
								Export Excel
							</Button>
						</div>
					</div>

					{mainTab === "marker" ? (
						<div className="space-y-3">
							<p className="text-xs leading-relaxed text-(--sea-ink-soft)">
								<strong className="text-(--sea-ink)">Perforation marker</strong>{" "}
								shows production rows after marker assignment and gap-fill. Sand
								columns use{" "}
								<code className="rounded bg-(--surface) px-1 text-(--sea-ink)">
									p
								</code>{" "}
								where that sand is open for the timestep (before KH split).
								Middle gaps left unresolved are flagged in warnings above — use
								<strong className="text-(--sea-ink)"> Data inputs</strong> to
								fix source data or add rows before re-running.
							</p>
							<ResultsTable
								rows={markerRows}
								maxRows={25}
								emptyMessage="No perforation preview rows."
							/>
						</div>
					) : (
						<div className="space-y-4">
							<div className="flex flex-wrap items-center gap-4">
								<Tabs
									items={SPLIT_TABS}
									value={splitSubTab}
									onChange={setSplitSubTab}
								/>
							</div>
							{splitSubTab === "summary" ? (
								<ResultsTable
									rows={summaryRows}
									maxRows={summaryRows.length}
									totalRows={summaryRows.length}
									emptyMessage="No summary rows."
								/>
							) : (
								<ResultsTable
									rows={detailRows}
									maxRows={25}
									emptyMessage="No detail rows."
								/>
							)}
						</div>
					)}
				</div>
			)}
		</div>
	);
}

function RunsHistory({
	runs,
	activeId,
	onSelect,
}: {
	runs: SplitRun[];
	activeId: number | null;
	onSelect: (id: number) => void;
}) {
	return (
		<div className="overflow-hidden rounded-2xl border border-(--line) bg-(--surface-strong)">
			<div className="flex items-center gap-2 border-b border-(--line)/70 bg-(--surface) px-4 py-2 text-xs font-semibold uppercase tracking-wider text-(--sea-ink-soft)">
				<History size={14} />
				Past runs
			</div>
			<ul className="divide-y divide-(--line)/40">
				{runs.map((run) => {
					const active = run.id === activeId;
					return (
						<li key={run.id}>
							<button
								type="button"
								onClick={() => onSelect(run.id)}
								className={`flex w-full items-center justify-between gap-3 px-4 py-2 text-left text-sm transition-colors hover:bg-(--surface) ${
									active
										? "bg-(--surface)/80 font-semibold text-(--sea-ink)"
										: "text-(--sea-ink)"
								}`}
							>
								<span className="flex items-center gap-2">
									<RunStatusBadge status={run.status} />
									Run #{run.id}
								</span>
								<span className="text-xs text-(--sea-ink-soft)">
									{new Date(run.created_at).toLocaleString()}
								</span>
							</button>
						</li>
					);
				})}
			</ul>
		</div>
	);
}

function RunMeta({ run }: { run: SplitRun }) {
	const datasetIds = run.dataset_ids ?? {};
	return (
		<div className="rounded-2xl border border-(--line) bg-(--surface-strong) p-4">
			<div className="flex flex-wrap items-center justify-between gap-3">
				<div className="flex items-center gap-3">
					<RunStatusBadge status={run.status} />
					<div>
						<p className="text-sm font-semibold text-(--sea-ink)">
							Run #{run.id}
						</p>
						<p className="text-xs text-(--sea-ink-soft)">
							Started {new Date(run.created_at).toLocaleString()}
							{run.completed_at ? (
								<>
									{" · "}
									Completed {new Date(run.completed_at).toLocaleString()}
								</>
							) : null}
						</p>
					</div>
				</div>
				<div className="flex flex-wrap gap-2 text-xs text-(--sea-ink-soft)">
					{Object.entries(datasetIds).map(([kind, id]) => (
						<span
							key={kind}
							className="rounded-full border border-(--line) bg-(--surface) px-2 py-0.5"
						>
							{kind} #{id}
						</span>
					))}
				</div>
			</div>
		</div>
	);
}

function WarningsBlock({ warnings }: { warnings: string[] }) {
	return (
		<div className="rounded-2xl border border-amber-200/80 bg-amber-50/80 p-4 text-sm text-amber-900">
			<div className="flex items-start gap-3">
				<AlertTriangle size={18} className="mt-0.5 shrink-0 text-amber-600" />
				<div>
					<p className="font-semibold">Run completed with warnings</p>
					<ul className="mt-2 list-disc space-y-1 pl-5 text-xs text-amber-800">
						{warnings.map((warning) => (
							<li key={warning}>{warning}</li>
						))}
					</ul>
				</div>
			</div>
		</div>
	);
}

function RunFailed({ run }: { run: SplitRun }) {
	return (
		<div className="rounded-2xl border border-red-200 bg-red-50/80 p-4 text-sm text-red-800">
			<div className="flex items-start gap-3">
				<XCircle size={18} className="mt-0.5 shrink-0 text-red-600" />
				<div>
					<p className="font-semibold">Run #{run.id} failed</p>
					<p className="mt-2 wrap-break-word text-xs">{run.error}</p>
				</div>
			</div>
		</div>
	);
}

function RunStatusBadge({ status }: { status: SplitRun["status"] }) {
	const config: Record<
		SplitRun["status"],
		{ label: string; className: string; Icon: typeof CheckCircle2 }
	> = {
		pending: {
			label: "Pending",
			className: "bg-(--surface) text-(--sea-ink-soft)",
			Icon: History,
		},
		running: {
			label: "Running",
			className: "bg-(--surface) text-(--lagoon-deep)",
			Icon: Play,
		},
		succeeded: {
			label: "Succeeded",
			className: "bg-emerald-50 text-emerald-700",
			Icon: CheckCircle2,
		},
		failed: {
			label: "Failed",
			className: "bg-red-50 text-red-700",
			Icon: XCircle,
		},
	};
	const { label, className, Icon } = config[status];
	return (
		<span
			className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[11px] font-semibold ${className}`}
		>
			<Icon size={12} />
			{label}
		</span>
	);
}

function EmptyState() {
	return (
		<div className="island-shell rounded-3xl p-10 text-center">
			<div className="mx-auto mb-3 grid h-10 w-10 place-items-center rounded-2xl bg-(--surface-strong) text-(--lagoon-deep) shadow-[0_1px_0_var(--inset-glint)_inset]">
				<Play size={18} />
			</div>
			<h2 className="display-title text-lg font-bold text-(--sea-ink)">
				No runs yet
			</h2>
			<p className="mx-auto mt-2 max-w-md text-sm text-(--sea-ink-soft)">
				Validate one of each required dataset (Marker, Marker List, Completion,
				Production, Lumping, Wells) under <strong>Data inputs</strong>, then
				click <strong>Run splitter</strong> to allocate volumes per sand.
			</p>
		</div>
	);
}
