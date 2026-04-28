import { useEffect, useMemo, useRef, useState } from "react";

import { Button } from "#/components/ui/button";
import { Modal } from "#/components/ui/modal";
import { Textarea } from "#/components/ui/textarea";
import { readErrorMessage } from "#/lib/api";
import { detectDelimiter, parseTable } from "#/lib/tabular";

import { usePasteDataset } from "./hooks";
import {
	DATASET_KIND_DESCRIPTIONS,
	DATASET_KIND_LABELS,
	type DatasetKind,
} from "./types";

type Props = {
	open: boolean;
	onClose: () => void;
	projectId: number;
	kind: DatasetKind;
};

export function PasteDialog({ open, onClose, projectId, kind }: Props) {
	const paste = usePasteDataset(projectId);
	const [text, setText] = useState("");
	const [error, setError] = useState<string | null>(null);
	const wasOpenRef = useRef(false);

	// biome-ignore lint/correctness/useExhaustiveDependencies: same as CreateProjectDialog — do not depend on `paste` / `paste.reset` or the effect loops after `reset()`.
	useEffect(() => {
		if (open && !wasOpenRef.current) {
			setText("");
			setError(null);
			paste.reset();
		}
		wasOpenRef.current = open;
	}, [open]);

	const preview = useMemo(() => {
		if (!text.trim()) return null;
		try {
			return parseTable(text);
		} catch {
			return null;
		}
	}, [text]);

	async function handleSubmit() {
		setError(null);
		if (!text.trim()) {
			setError("Paste at least a header row and one data row.");
			return;
		}
		const parsed = parseTable(text);
		if (parsed.headers.length === 0) {
			setError("No headers detected.");
			return;
		}
		if (parsed.rows.length === 0) {
			setError(
				"No data rows detected. Make sure to include at least one row below the header.",
			);
			return;
		}
		try {
			await paste.mutateAsync({ kind, data: parsed.rows });
			onClose();
		} catch (err) {
			setError(await readErrorMessage(err));
		}
	}

	const delimiter = useMemo(
		() => (text.trim() ? detectDelimiter(text) : null),
		[text],
	);
	const delimiterLabel =
		delimiter === "\t"
			? "tab"
			: delimiter === ";"
				? "semicolon"
				: delimiter
					? "comma"
					: null;

	return (
		<Modal
			open={open}
			onClose={onClose}
			size="lg"
			title={`Paste ${DATASET_KIND_LABELS[kind]} data`}
			description={DATASET_KIND_DESCRIPTIONS[kind]}
			footer={
				<>
					<Button variant="ghost" type="button" onClick={onClose}>
						Cancel
					</Button>
					<Button onClick={handleSubmit} isLoading={paste.isPending}>
						Validate &amp; save
					</Button>
				</>
			}
		>
			<div className="space-y-3">
				<p className="text-sm text-(--sea-ink-soft)">
					Copy a range from your spreadsheet (including the header row) and
					paste it below. Tabs, commas, and semicolons are all auto-detected.
				</p>
				<Textarea
					value={text}
					onChange={(e) => setText(e.target.value)}
					placeholder="Paste TSV / CSV here…"
					className="min-h-56"
					autoFocus
				/>
				<div className="flex items-center justify-between text-xs text-(--sea-ink-soft)">
					<span>
						{preview
							? `${preview.rows.length} row${preview.rows.length === 1 ? "" : "s"} · ${preview.headers.length} column${preview.headers.length === 1 ? "" : "s"}`
							: "Awaiting paste…"}
					</span>
					{delimiterLabel ? <span>Delimiter: {delimiterLabel}</span> : null}
				</div>

				{error ? (
					<div
						role="alert"
						className="rounded-xl border border-red-200/70 bg-red-50/80 px-3 py-2 text-sm text-red-700"
					>
						{error}
					</div>
				) : null}
			</div>
		</Modal>
	);
}
