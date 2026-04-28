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
	detail: Array<Record<string, unknown>> | null;
	summary: Array<Record<string, unknown>> | null;
};

export type RunTable = "detail" | "summary";
export type ExportFormat = "csv" | "xlsx";
