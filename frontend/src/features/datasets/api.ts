import { api } from "#/lib/api";

import type {
	Dataset,
	DatasetDetail,
	DatasetKind,
	DatasetPasteRequest,
} from "./types";

export async function listDatasets(
	projectId: number,
	kind?: DatasetKind,
): Promise<Dataset[]> {
	const searchParams = kind ? { kind } : undefined;
	return api
		.get(`projects/${projectId}/datasets`, { searchParams })
		.json<Dataset[]>();
}

export async function getDataset(
	projectId: number,
	datasetId: number,
): Promise<DatasetDetail> {
	return api
		.get(`projects/${projectId}/datasets/${datasetId}`)
		.json<DatasetDetail>();
}

export async function pasteDataset(
	projectId: number,
	payload: DatasetPasteRequest,
): Promise<Dataset> {
	return api
		.post(`projects/${projectId}/datasets/paste`, { json: payload })
		.json<Dataset>();
}

export async function uploadDataset(
	projectId: number,
	args: { file: File; kind: DatasetKind; sheetName?: string },
): Promise<Dataset> {
	const form = new FormData();
	form.append("file", args.file);
	form.append("kind", args.kind);
	if (args.sheetName) form.append("sheet_name", args.sheetName);
	return api
		.post(`projects/${projectId}/datasets/upload`, { body: form })
		.json<Dataset>();
}

export async function listWorkbookSheets(
	projectId: number,
	file: File,
): Promise<string[]> {
	const form = new FormData();
	form.append("file", file);
	const result = await api
		.post(`projects/${projectId}/datasets/workbook-sheets`, { body: form })
		.json<{ sheets: string[] }>();
	return result.sheets;
}

export async function deleteDataset(
	projectId: number,
	datasetId: number,
): Promise<void> {
	await api.delete(`projects/${projectId}/datasets/${datasetId}`);
}
