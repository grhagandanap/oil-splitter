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
};

export function PreviewTable({ rows, maxRows = 25 }: Props) {
	const visible = useMemo(() => rows.slice(0, maxRows), [rows, maxRows]);

	const columns = useMemo<ColumnDef<Record<string, unknown>>[]>(() => {
		if (visible.length === 0) return [];
		const headers = Object.keys(visible[0]);
		return headers.map((header) => ({
			accessorKey: header,
			header,
			cell: ({ getValue }) => formatCell(getValue()),
		}));
	}, [visible]);

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
			{rows.length > maxRows ? (
				<div className="border-t border-(--line)/70 bg-(--surface) px-3 py-2 text-center text-xs text-(--sea-ink-soft)">
					Showing first {maxRows} of {rows.length} rows
				</div>
			) : null}
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
