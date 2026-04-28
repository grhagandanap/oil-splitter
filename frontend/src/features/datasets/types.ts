export type DatasetKind =
	| "marker"
	| "sand"
	| "completion"
	| "production"
	| "lumping"
	| "well";

export type ValidationError = {
	row: number;
	column: string;
	message: string;
};

export type Dataset = {
	id: number;
	project_id: number;
	kind: DatasetKind;
	source: string;
	filename: string | null;
	row_count: number;
	is_valid: boolean;
	validation_errors: ValidationError[] | null;
	created_at: string;
};

export type DatasetDetail = Dataset & {
	raw_data: Array<Record<string, unknown>> | null;
};

export type DatasetPasteRequest = {
	kind: DatasetKind;
	data: Array<Record<string, unknown>>;
};

export const DATASET_KINDS: DatasetKind[] = [
	"marker",
	"sand",
	"completion",
	"production",
	"lumping",
	"well",
];

export const DATASET_KIND_LABELS: Record<DatasetKind, string> = {
	marker: "Marker",
	sand: "Marker List",
	completion: "Completion",
	production: "Production",
	lumping: "Lumping",
	well: "Wells",
};

export const DATASET_KIND_DESCRIPTIONS: Record<DatasetKind, string> = {
	marker: "Per-well marker depths.",
	sand: "Master ordered list of markers.",
	completion:
		"Perforation & squeeze events with status, top depth, and bottom depth.",
	production:
		"Time series per well. Include one or more fluid columns: Oil, Water, Gas, Water Injection.",
	lumping:
		"Long-format zone/well/lumping input. Backend pivots Zone as rows, Well as columns, and Lumping as values.",
	well: "Master well list.",
};

export const DATASET_REQUIRED_COLUMNS: Record<DatasetKind, string[]> = {
	marker: ["Well", "Marker", "Depth"],
	sand: ["Marker"],
	completion: ["Well", "Date", "Perf Status", "Perf Top", "Perf Bottom"],
	production: [
		"Well",
		"Date",
		"Oil and/or Water and/or Gas and/or Water Injection",
	],
	lumping: ["Zone", "Well", "Lumping"],
	well: ["Well"],
};

/**
 * Canonical column order shown in the preview table after ingestion. Any
 * columns not in this list (e.g. dynamic well columns from a pivoted lumping
 * matrix) are appended afterwards in the order they were received.
 */
export const DATASET_PREVIEW_COLUMN_ORDER: Record<DatasetKind, string[]> = {
	marker: ["Well", "Marker", "Depth"],
	sand: ["Marker"],
	completion: ["Well", "Date", "Perf Status", "Perf Top", "Perf Bottom"],
	production: ["Well", "Date", "Oil", "Water", "Gas", "Water Injection"],
	lumping: ["Zone"],
	well: ["Well"],
};

export const DATASET_COLUMN_NOTES: Record<DatasetKind, string> = {
	marker:
		"Use one row per well-marker depth. Column order can be arbitrary as long as required names exist.",
	sand: "Use this to define marker order. Column order can be arbitrary as long as required names exist.",
	completion:
		"Column order can be arbitrary. Perf Status must be perforation or squeeze. Perf Bottom must be deeper than Perf Top.",
	production:
		"Column order can be arbitrary. Oil, Water, Gas, and Water Injection are optional individually, but at least one fluid column must exist and all included fluid cells must be filled.",
	lumping:
		"Column order can be arbitrary. Upload long format only: Zone, Well, Lumping. The backend will pivot it to Zone rows and Well columns.",
	well: "Use one Well value per row. Column order can be arbitrary as long as required names exist.",
};
