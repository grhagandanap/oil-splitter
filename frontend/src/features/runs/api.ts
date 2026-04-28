import { api } from "#/lib/api";
import { tokenStore } from "#/lib/auth-storage";

import type { ExportFormat, RunTable, SplitRun, SplitRunDetail } from "./types";

export async function listRuns(projectId: number): Promise<SplitRun[]> {
	return api.get(`projects/${projectId}/split/runs`).json<SplitRun[]>();
}

export async function getRun(
	projectId: number,
	runId: number,
): Promise<SplitRunDetail> {
	return api
		.get(`projects/${projectId}/split/runs/${runId}`)
		.json<SplitRunDetail>();
}

export async function startRun(projectId: number): Promise<SplitRunDetail> {
	return api.post(`projects/${projectId}/split/run`).json<SplitRunDetail>();
}

/**
 * Trigger a browser download of the full ``detail`` or ``summary`` table.
 *
 * Uses ``fetch`` directly (rather than the ``ky`` wrapper) because we need
 * the raw ``Blob`` and full control over the download anchor. Auth header is
 * attached manually from ``tokenStore``.
 */
export async function downloadRunExport(
	projectId: number,
	runId: number,
	args: { table: RunTable; format: ExportFormat },
): Promise<void> {
	const baseUrl =
		(import.meta.env.VITE_API_BASE_URL as string | undefined) ??
		"http://localhost:8000/api/v1";
	const trimmed = baseUrl.endsWith("/") ? baseUrl.slice(0, -1) : baseUrl;
	const url = new URL(
		`${trimmed}/projects/${projectId}/split/runs/${runId}/export`,
	);
	url.searchParams.set("table", args.table);
	url.searchParams.set("format", args.format);

	const access = tokenStore.getAccess();
	const response = await fetch(url, {
		headers: access ? { Authorization: `Bearer ${access}` } : undefined,
	});
	if (!response.ok) {
		const message = await response.text().catch(() => response.statusText);
		throw new Error(message || "Export failed");
	}

	const blob = await response.blob();
	const objectUrl = URL.createObjectURL(blob);
	const anchor = document.createElement("a");
	anchor.href = objectUrl;
	anchor.download = `split_run_${runId}_${args.table}.${args.format}`;
	document.body.appendChild(anchor);
	anchor.click();
	anchor.remove();
	URL.revokeObjectURL(objectUrl);
}
