import {
	type ColumnDef,
	flexRender,
	getCoreRowModel,
	useReactTable,
} from "@tanstack/react-table";
import { useMemo } from "react";
import { DATASET_PREVIEW_COLUMN_ORDER, type DatasetKind } from "./types";

type Props = {
	rows: Array<Record<string, unknown>>;
	maxRows?: number;
	kind?: DatasetKind;
	/**
	 * Canonical full size of the underlying dataset. The API only returns a
	 * truncated slice of `raw_data` for performance, so falling back to
	 * `rows.length` would understate the true row count.
	 */
	totalRows?: number;
};

export function PreviewTable({
	rows,
	maxRows = 15,
	kind,
	totalRows,
}: Props) {
	const visible = useMemo(() => rows.slice(0, maxRows), [rows, maxRows]);

	const orderedHeaders = useMemo(() => {
		if (visible.length === 0) return [] as string[];
		const present = new Set<string>();
		for (const row of visible) {
			for (const key of Object.keys(row)) present.add(key);
		}
		const preferred = kind ? DATASET_PREVIEW_COLUMN_ORDER[kind] : [];
		const ordered: string[] = [];
		for (const key of preferred) {
			if (present.has(key)) {
				ordered.push(key);
				present.delete(key);
			}
		}
		// Append remaining headers in their original encounter order.
		const firstRowKeys = Object.keys(visible[0]);
		for (const key of firstRowKeys) {
			if (present.has(key)) {
				ordered.push(key);
				present.delete(key);
			}
		}
		for (const key of present) ordered.push(key);
		return ordered;
	}, [visible, kind]);

	const columns = useMemo<ColumnDef<Record<string, unknown>>[]>(
		() =>
			orderedHeaders.map((header) => ({
				accessorKey: header,
				header,
				cell: ({ getValue }) => formatCell(getValue()),
			})),
		[orderedHeaders],
	);

	const table = useReactTable({
		data: visible,
		columns,
		getCoreRowModel: getCoreRowModel(),
	});

	if (rows.length === 0) {
		return (
			<div className="rounded-2xl border border-dashed border-(--line) bg-(--surface)/60 p-8 text-center text-sm text-(--sea-ink-soft)">
				No rows to preview.
			</div>
		);
	}

	return (
		<div className="overflow-hidden rounded-2xl border border-(--line) bg-(--surface-strong) shadow-[inset_0_1px_0_var(--inset-glint)]">
			<div className="overflow-x-auto">
				<table className="min-w-full text-sm">
					<thead className="bg-(--surface)">
						{table.getHeaderGroups().map((group) => (
							<tr key={group.id}>
								{group.headers.map((header) => (
									<th
										key={header.id}
										className="border-b border-(--line)/70 px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wider text-(--sea-ink-soft)"
									>
										{flexRender(
											header.column.columnDef.header,
											header.getContext(),
										)}
									</th>
								))}
							</tr>
						))}
					</thead>
					<tbody>
						{table.getRowModel().rows.map((row, idx) => (
							<tr
								key={row.id}
								className={
									idx % 2 === 0 ? "bg-(--surface-strong)" : "bg-(--surface)"
								}
							>
								{row.getVisibleCells().map((cell) => (
									<td
										key={cell.id}
										className="border-b border-(--line)/40 px-3 py-2 align-top text-(--sea-ink)"
									>
										{flexRender(cell.column.columnDef.cell, cell.getContext())}
									</td>
								))}
							</tr>
						))}
					</tbody>
				</table>
			</div>
			{(() => {
				const total = totalRows ?? rows.length;
				const shown = Math.min(visible.length, total);
				if (total <= shown) return null;
				return (
					<div className="border-t border-(--line)/70 bg-(--surface) px-3 py-2 text-center text-xs text-(--sea-ink-soft)">
						Showing first {shown} of {total.toLocaleString()} rows
					</div>
				);
			})()}
		</div>
	);
}

function formatCell(value: unknown): string {
	if (value === null || value === undefined) return "—";
	if (typeof value === "number")
		return Number.isInteger(value) ? String(value) : value.toFixed(4);
	if (typeof value === "string") return value;
	return JSON.stringify(value);
}
