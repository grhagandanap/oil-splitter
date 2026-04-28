import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
	deleteDataset,
	getDataset,
	listDatasets,
	pasteDataset,
	uploadDataset,
} from "./api";
import type {
	Dataset,
	DatasetDetail,
	DatasetKind,
	DatasetPasteRequest,
} from "./types";

export const datasetKeys = {
	all: ["datasets"] as const,
	list: (projectId: number, kind?: DatasetKind) =>
		[...datasetKeys.all, "list", projectId, kind ?? "all"] as const,
	detail: (projectId: number, datasetId: number) =>
		[...datasetKeys.all, "detail", projectId, datasetId] as const,
};

export function useDatasets(projectId: number | undefined, kind?: DatasetKind) {
	return useQuery<Dataset[]>({
		queryKey: datasetKeys.list(projectId ?? -1, kind),
		queryFn: () => listDatasets(projectId as number, kind),
		enabled: typeof projectId === "number",
	});
}

export function useDataset(projectId: number, datasetId: number | undefined) {
	return useQuery<DatasetDetail>({
		queryKey: datasetId
			? datasetKeys.detail(projectId, datasetId)
			: ["datasets", "detail", projectId, "noop"],
		queryFn: () => getDataset(projectId, datasetId as number),
		enabled: typeof datasetId === "number",
	});
}

function invalidateLists(
	qc: ReturnType<typeof useQueryClient>,
	projectId: number,
) {
	void qc.invalidateQueries({
		queryKey: [...datasetKeys.all, "list", projectId],
	});
}

export function usePasteDataset(projectId: number) {
	const qc = useQueryClient();
	return useMutation<Dataset, Error, DatasetPasteRequest>({
		mutationFn: (payload) => pasteDataset(projectId, payload),
		onSuccess: () => invalidateLists(qc, projectId),
	});
}

export function useUploadDataset(projectId: number) {
	const qc = useQueryClient();
	return useMutation<
		Dataset,
		Error,
		{ file: File; kind: DatasetKind; sheetName?: string }
	>({
		mutationFn: (args) => uploadDataset(projectId, args),
		onSuccess: () => invalidateLists(qc, projectId),
	});
}

export function useDeleteDataset(projectId: number) {
	const qc = useQueryClient();
	return useMutation<void, Error, number>({
		mutationFn: (datasetId) => deleteDataset(projectId, datasetId),
		onSuccess: () => invalidateLists(qc, projectId),
	});
}
