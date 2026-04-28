import { AlertTriangle, CheckCircle2 } from "lucide-react";

import type { ValidationError } from "./types";

type Props = {
	errors: ValidationError[] | null | undefined;
	totalRows: number;
};

export function ValidationErrorsPanel({ errors, totalRows }: Props) {
	if (!errors || errors.length === 0) {
		return (
			<div className="flex items-start gap-3 rounded-2xl border border-(--palm)/30 bg-(--palm)/8 px-4 py-3 text-sm text-(--palm)">
				<CheckCircle2 size={18} className="mt-0.5 shrink-0" />
				<div>
					<p className="font-semibold">All checks passed</p>
					<p className="text-(--palm)/85">
						{totalRows} row{totalRows === 1 ? "" : "s"} validated successfully.
					</p>
				</div>
			</div>
		);
	}

	return (
		<div className="rounded-2xl border border-red-200/70 bg-red-50/70">
			<header className="flex items-center gap-2 border-b border-red-200/70 px-4 py-3 text-sm font-semibold text-red-700">
				<AlertTriangle size={16} />
				<span>
					{errors.length} validation issue{errors.length === 1 ? "" : "s"}
				</span>
			</header>
			<div className="max-h-72 overflow-y-auto">
				<table className="min-w-full text-sm">
					<thead className="bg-red-50/90">
						<tr>
							<th className="px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wider text-red-700/80">
								Row
							</th>
							<th className="px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wider text-red-700/80">
								Column
							</th>
							<th className="px-3 py-2 text-left text-[11px] font-semibold uppercase tracking-wider text-red-700/80">
								Message
							</th>
						</tr>
					</thead>
					<tbody>
						{errors.map((err, idx) => (
							<tr
								key={`${err.row}-${err.column}-${err.message}`}
								className={idx % 2 === 0 ? "bg-red-50/30" : "bg-red-50/60"}
							>
								<td className="px-3 py-2 align-top font-mono text-xs text-red-700">
									{err.row}
								</td>
								<td className="px-3 py-2 align-top text-red-800">
									{err.column}
								</td>
								<td className="px-3 py-2 align-top text-red-900">
									{err.message}
								</td>
							</tr>
						))}
					</tbody>
				</table>
			</div>
		</div>
	);
}
