import { useQueries } from "@tanstack/react-query";
import { Database } from "lucide-react";
import { useMemo } from "react";

import { Spinner } from "#/components/ui/spinner";

import { getDataset } from "./api";
import { datasetKeys, useDatasets } from "./hooks";
import {
	DATASET_KIND_LABELS,
	type DatasetDetail,
	type DatasetKind,
} from "./types";

type Props = {
	projectId: number;
};

const SCANNED_KINDS: DatasetKind[] = ["marker", "completion", "production"];

export function WellsOverview({ projectId }: Props) {
	const allQuery = useDatasets(projectId);

	const latestPerKind = useMemo(() => {
		const map = new Map<DatasetKind, number>();
		if (!allQuery.data) return map;
		for (const ds of allQuery.data) {
			if (!SCANNED_KINDS.includes(ds.kind)) continue;
			if (!map.has(ds.kind)) map.set(ds.kind, ds.id);
		}
		return map;
	}, [allQuery.data]);

	const detailQueries = useQueries({
		queries: SCANNED_KINDS.map((kind) => {
			const datasetId = latestPerKind.get(kind);
			return {
				queryKey: datasetId
					? datasetKeys.detail(projectId, datasetId)
					: ["datasets", "detail", projectId, "noop", kind],
				queryFn: () => getDataset(projectId, datasetId as number),
				enabled: typeof datasetId === "number",
			};
		}),
	});

	const wellsByKind = useMemo(() => {
		const map = new Map<DatasetKind, Set<string>>();
		SCANNED_KINDS.forEach((kind, idx) => {
			const set = new Set<string>();
			const detail = detailQueries[idx]?.data as DatasetDetail | undefined;
			for (const row of detail?.raw_data ?? []) {
				const well = row.WELL;
				if (typeof well === "string" && well.trim()) set.add(well.trim());
				else if (typeof well === "number") set.add(String(well));
			}
			map.set(kind, set);
		});
		return map;
	}, [detailQueries]);

	const allWells = useMemo(() => {
		const set = new Set<string>();
		for (const wells of wellsByKind.values()) {
			for (const w of wells) set.add(w);
		}
		return Array.from(set).sort();
	}, [wellsByKind]);

	const isLoading =
		allQuery.isPending ||
		detailQueries.some((q) => q.isPending && q.fetchStatus !== "idle");

	if (isLoading) {
		return (
			<div className="flex items-center gap-2 text-sm text-(--sea-ink-soft)">
				<Spinner size="sm" />
				Scanning your datasets…
			</div>
		);
	}

	return (
		<div className="space-y-5">
			<header>
				<h2 className="display-title text-xl font-bold text-(--sea-ink)">
					Wells overview
				</h2>
				<p className="mt-1 max-w-2xl text-sm text-(--sea-ink-soft)">
					Aggregated list of wells discovered across the latest marker,
					completion, and production uploads. Spot wells that are missing from
					one of the inputs before running the splitter.
				</p>
			</header>

			{allWells.length === 0 ? (
				<div className="island-shell rounded-3xl p-8 text-center">
					<div className="mx-auto mb-3 grid h-10 w-10 place-items-center rounded-2xl bg-(--surface-strong) text-(--lagoon-deep) shadow-[0_1px_0_var(--inset-glint)_inset]">
						<Database size={18} />
					</div>
					<p className="text-sm text-(--sea-ink-soft)">
						Upload marker, completion, or production data to populate this
						overview.
					</p>
				</div>
			) : (
				<div className="overflow-hidden rounded-2xl border border-(--line) bg-(--surface-strong)">
					<table className="min-w-full text-sm">
						<thead className="bg-(--surface)">
							<tr>
								<th className="px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wider text-(--sea-ink-soft)">
									Well
								</th>
								{SCANNED_KINDS.map((kind) => (
									<th
										key={kind}
										className="px-3 py-2 text-center text-[11px] font-semibold uppercase tracking-wider text-(--sea-ink-soft)"
									>
										{DATASET_KIND_LABELS[kind]}
									</th>
								))}
							</tr>
						</thead>
						<tbody>
							{allWells.map((well, idx) => (
								<tr
									key={well}
									className={
										idx % 2 === 0 ? "bg-(--surface-strong)" : "bg-(--surface)"
									}
								>
									<td className="px-3 py-2 align-top font-semibold text-(--sea-ink)">
										{well}
									</td>
									{SCANNED_KINDS.map((kind) => {
										const present = wellsByKind.get(kind)?.has(well) ?? false;
										return (
											<td key={kind} className="px-3 py-2 text-center">
												{present ? (
													<span className="inline-flex items-center justify-center rounded-full bg-(--palm)/12 px-2 py-0.5 text-xs font-semibold text-(--palm)">
														✓
													</span>
												) : (
													<span className="inline-flex items-center justify-center rounded-full bg-red-100/60 px-2 py-0.5 text-xs font-semibold text-red-700">
														missing
													</span>
												)}
											</td>
										);
									})}
								</tr>
							))}
						</tbody>
					</table>
				</div>
			)}
		</div>
	);
}
