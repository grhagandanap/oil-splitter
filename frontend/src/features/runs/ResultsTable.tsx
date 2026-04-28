import {
	type ColumnDef,
	flexRender,
	getCoreRowModel,
	useReactTable,
} from "@tanstack/react-table";
import { useMemo } from "react";

type Props = {
	rows: Array<Record<string, unknown>>;
	maxRows?: number;
	totalRows?: number;
	emptyMessage?: string;
};

export function ResultsTable({
	rows,
	maxRows = 25,
	totalRows,
	emptyMessage = "No rows to show.",
}: Props) {
	const visible = useMemo(() => rows.slice(0, maxRows), [rows, maxRows]);

	const headers = useMemo(() => {
		if (visible.length === 0) return [] as string[];
		const seen = new Set<string>();
		const ordered: string[] = [];
		for (const row of visible) {
			for (const key of Object.keys(row)) {
				if (!seen.has(key)) {
					seen.add(key);
					ordered.push(key);
				}
			}
		}
		return ordered;
	}, [visible]);

	const columns = useMemo<ColumnDef<Record<string, unknown>>[]>(
		() =>
			headers.map((header) => ({
				accessorKey: header,
				header,
				cell: ({ getValue }) => formatCell(getValue()),
			})),
		[headers],
	);

	const table = useReactTable({
		data: visible,
		columns,
		getCoreRowModel: getCoreRowModel(),
	});

	if (rows.length === 0) {
		return (
			<div className="rounded-2xl border border-dashed border-(--line) bg-(--surface)/60 p-8 text-center text-sm text-(--sea-ink-soft)">
				{emptyMessage}
			</div>
		);
	}

	const total = totalRows ?? rows.length;
	const shown = Math.min(visible.length, total);

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
										className="whitespace-nowrap border-b border-(--line)/40 px-3 py-2 align-top text-(--sea-ink)"
									>
										{flexRender(cell.column.columnDef.cell, cell.getContext())}
									</td>
								))}
							</tr>
						))}
					</tbody>
				</table>
			</div>
			{total > shown ? (
				<div className="border-t border-(--line)/70 bg-(--surface) px-3 py-2 text-center text-xs text-(--sea-ink-soft)">
					Showing first {shown} of {total.toLocaleString()} rows
				</div>
			) : null}
		</div>
	);
}

function formatCell(value: unknown): string {
	if (value === null || value === undefined) return "—";
	if (typeof value === "number") {
		if (Number.isInteger(value)) return String(value);
		const abs = Math.abs(value);
		if (abs > 0 && abs < 0.01) return value.toExponential(3);
		return value.toFixed(4);
	}
	if (typeof value === "string") return value;
	if (Array.isArray(value)) return value.map((v) => String(v)).join(", ");
	return JSON.stringify(value);
}
