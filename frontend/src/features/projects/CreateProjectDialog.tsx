import { type FormEvent, useEffect, useRef, useState } from "react";

import { Button } from "#/components/ui/button";
import { Input } from "#/components/ui/input";
import { Label } from "#/components/ui/label";
import { Modal } from "#/components/ui/modal";
import { Textarea } from "#/components/ui/textarea";
import { readErrorMessage } from "#/lib/api";

import { useCreateProject } from "./hooks";

type Props = {
	open: boolean;
	onClose: () => void;
	onCreated?: (projectId: number) => void;
};

export function CreateProjectDialog({ open, onClose, onCreated }: Props) {
	const create = useCreateProject();
	const [name, setName] = useState("");
	const [description, setDescription] = useState("");
	const [error, setError] = useState<string | null>(null);
	const wasOpenRef = useRef(false);

	// biome-ignore lint/correctness/useExhaustiveDependencies: `create.reset()` updates the mutation object; putting `create` or `reset` in deps re-ran this effect forever ("Maximum update depth exceeded").
	useEffect(() => {
		if (open && !wasOpenRef.current) {
			setName("");
			setDescription("");
			setError(null);
			create.reset();
		}
		wasOpenRef.current = open;
	}, [open]);

	async function handleSubmit(event: FormEvent<HTMLFormElement>) {
		event.preventDefault();
		setError(null);
		if (!name.trim()) {
			setError("Project name is required.");
			return;
		}
		try {
			const project = await create.mutateAsync({
				name: name.trim(),
				description: description.trim() || null,
			});
			onCreated?.(project.id);
			onClose();
		} catch (err) {
			setError(await readErrorMessage(err));
		}
	}

	return (
		<Modal
			open={open}
			onClose={onClose}
			title="Create a new project"
			description="Group datasets and runs per field, well group, or campaign."
			size="md"
			footer={
				<>
					<Button variant="ghost" type="button" onClick={onClose}>
						Cancel
					</Button>
					<Button
						type="submit"
						form="create-project-form"
						isLoading={create.isPending}
					>
						Create project
					</Button>
				</>
			}
		>
			<form
				id="create-project-form"
				onSubmit={handleSubmit}
				className="space-y-4"
				noValidate
			>
				<div className="space-y-1.5">
					<Label htmlFor="project-name">Project name</Label>
					<Input
						id="project-name"
						value={name}
						onChange={(e) => setName(e.target.value)}
						placeholder="e.g. East Block — 2025 Allocation"
						autoFocus
						required
					/>
				</div>

				<div className="space-y-1.5">
					<Label htmlFor="project-description">Description</Label>
					<Textarea
						id="project-description"
						value={description}
						onChange={(e) => setDescription(e.target.value)}
						placeholder="Optional notes for your team."
						className="min-h-24 font-sans"
					/>
				</div>

				{error ? (
					<div
						role="alert"
						className="rounded-xl border border-red-200/70 bg-red-50/80 px-3 py-2 text-sm text-red-700"
					>
						{error}
					</div>
				) : null}
			</form>
		</Modal>
	);
}
