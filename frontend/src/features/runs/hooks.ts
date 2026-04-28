import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getRun, listRuns, startRun } from "./api";
import type { SplitRun, SplitRunDetail } from "./types";

export const runKeys = {
	all: ["runs"] as const,
	list: (projectId: number) => [...runKeys.all, "list", projectId] as const,
	detail: (projectId: number, runId: number) =>
		[...runKeys.all, "detail", projectId, runId] as const,
};

export function useRuns(projectId: number | undefined) {
	return useQuery<SplitRun[]>({
		queryKey: runKeys.list(projectId ?? -1),
		queryFn: () => listRuns(projectId as number),
		enabled: typeof projectId === "number",
	});
}

export function useRun(projectId: number, runId: number | undefined) {
	return useQuery<SplitRunDetail>({
		queryKey: runId
			? runKeys.detail(projectId, runId)
			: ["runs", "detail", projectId, "noop"],
		queryFn: () => getRun(projectId, runId as number),
		enabled: typeof runId === "number",
	});
}

export function useStartRun(projectId: number) {
	const qc = useQueryClient();
	return useMutation<SplitRunDetail, Error, void>({
		mutationFn: () => startRun(projectId),
		onSuccess: (run) => {
			void qc.invalidateQueries({ queryKey: runKeys.list(projectId) });
			qc.setQueryData(runKeys.detail(projectId, run.id), run);
		},
	});
}
