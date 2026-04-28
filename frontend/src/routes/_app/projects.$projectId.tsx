import {
	createFileRoute,
	Link,
	useNavigate,
	useParams,
} from "@tanstack/react-router";
import {
	ArrowLeft,
	ChartLine,
	ClipboardList,
	Database,
	Layers,
	LineChart,
	PackageSearch,
	Wrench,
} from "lucide-react";
import { useState } from "react";

import { Spinner } from "#/components/ui/spinner";
import { type TabItem, Tabs } from "#/components/ui/tabs";
import { DatasetPanel } from "#/features/datasets/DatasetPanel";
import type { DatasetKind } from "#/features/datasets/types";
import { useProject } from "#/features/projects/hooks";
import { ResultsPanel } from "#/features/runs/ResultsPanel";

export const Route = createFileRoute("/_app/projects/$projectId")({
	component: ProjectDetailPage,
});

type TopTab = "inputs" | "results";
type InputTab = DatasetKind;

const TOP_TABS: TabItem<TopTab>[] = [
	{ value: "inputs", label: "Data inputs", icon: <Database size={14} /> },
	{ value: "results", label: "Results", icon: <LineChart size={14} /> },
];

const INPUT_TABS: TabItem<InputTab>[] = [
	{ value: "marker", label: "Marker", icon: <Layers size={14} /> },
	{ value: "sand", label: "Marker List", icon: <PackageSearch size={14} /> },
	{ value: "completion", label: "Completion", icon: <Wrench size={14} /> },
	{ value: "production", label: "Production", icon: <ChartLine size={14} /> },
	{ value: "lumping", label: "Lumping", icon: <ClipboardList size={14} /> },
	{ value: "well", label: "Wells", icon: <Database size={14} /> },
];

function ProjectDetailPage() {
	const { projectId } = useParams({ from: "/_app/projects/$projectId" });
	const navigate = useNavigate();
	const projectIdNum = Number(projectId);
	const projectQuery = useProject(projectIdNum);

	const [topTab, setTopTab] = useState<TopTab>("inputs");
	const [inputTab, setInputTab] = useState<InputTab>("marker");

	if (projectQuery.isPending) {
		return (
			<div className="page-wrap flex min-h-[60vh] items-center justify-center">
				<Spinner size="md" />
				<span className="ml-3 text-(--sea-ink-soft)">Loading project…</span>
			</div>
		);
	}

	if (projectQuery.isError || !projectQuery.data) {
		return (
			<div className="page-wrap py-10">
				<div className="island-shell mx-auto max-w-lg rounded-3xl p-8 text-center">
					<h2 className="display-title text-xl font-bold text-(--sea-ink)">
						Project not found
					</h2>
					<p className="mt-2 text-sm text-(--sea-ink-soft)">
						The project you’re looking for doesn’t exist or you don’t have
						access to it.
					</p>
					<Link
						to="/dashboard"
						className="mt-4 inline-flex items-center gap-1 text-sm font-semibold no-underline text-(--lagoon-deep)"
						onClick={(e) => {
							e.preventDefault();
							void navigate({ to: "/dashboard" });
						}}
					>
						<ArrowLeft size={14} />
						Back to projects
					</Link>
				</div>
			</div>
		);
	}

	const project = projectQuery.data;

	return (
		<div className="page-wrap py-10">
			<header className="rise-in mb-8">
				<Link
					to="/dashboard"
					className="inline-flex items-center gap-1 text-xs font-semibold uppercase tracking-wider no-underline text-(--sea-ink-soft) hover:text-(--sea-ink)"
				>
					<ArrowLeft size={12} />
					All projects
				</Link>
				<h1 className="display-title mt-2 text-3xl font-bold text-(--sea-ink) md:text-4xl">
					{project.name}
				</h1>
				{project.description ? (
					<p className="mt-2 max-w-2xl text-(--sea-ink-soft)">
						{project.description}
					</p>
				) : null}
			</header>

			<div className="mb-6">
				<Tabs
					items={TOP_TABS}
					value={topTab}
					onChange={setTopTab}
					variant="underline"
				/>
			</div>

			{topTab === "inputs" ? (
				<div className="space-y-6">
					<Tabs items={INPUT_TABS} value={inputTab} onChange={setInputTab} />
					<div className="island-shell rounded-3xl p-6">
						<DatasetPanel projectId={projectIdNum} kind={inputTab} />
					</div>
				</div>
			) : (
				<div className="island-shell rounded-3xl p-6">
					<ResultsPanel projectId={projectIdNum} />
				</div>
			)}
		</div>
	);
}
