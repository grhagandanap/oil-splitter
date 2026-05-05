export type SplitRunStatus = "pending" | "running" | "succeeded" | "failed";

export type SplitRun = {
	id: number;
	project_id: number;
	status: SplitRunStatus;
	error: string | null;
	dataset_ids: Record<string, number> | null;
	warnings: string[] | null;
	created_at: string;
	completed_at: string | null;
};

export type SplitRunDetail = SplitRun & {
	/** Markered production after gap-fill: Well/Date/fluids + sand columns with ``p``. */
	marker_preview: Array<Record<string, unknown>> | null;
	detail: Array<Record<string, unknown>> | null;
	summary: Array<Record<string, unknown>> | null;
};

/** Table passed to ``/export`` — ``marker`` is the perforation / ``p`` view. */
export type RunTable = "detail" | "summary" | "marker";
export type ExportFormat = "csv" | "xlsx";
