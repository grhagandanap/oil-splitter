import { TanStackDevtools } from "@tanstack/react-devtools";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
	createRootRoute,
	HeadContent,
	Link,
	Scripts,
} from "@tanstack/react-router";
import { TanStackRouterDevtoolsPanel } from "@tanstack/react-router-devtools";
import { type ReactNode, useState } from "react";
import { SiteFooter } from "#/components/site-footer";
import { SiteHeader } from "#/components/site-header";
import { AuthProvider } from "#/features/auth/AuthProvider";

import appCss from "../styles.css?url";

function RootNotFound() {
	return (
		<div className="page-wrap py-20 text-center">
			<h1 className="display-title text-2xl font-bold text-(--sea-ink)">
				Page not found
			</h1>
			<p className="mt-2 text-sm text-(--sea-ink-soft)">
				That URL does not match any route in this app.
			</p>
			<p className="mt-6">
				<Link
					to="/"
					className="font-semibold text-(--lagoon-deep) no-underline"
				>
					Go home
				</Link>
			</p>
		</div>
	);
}

export const Route = createRootRoute({
	notFoundComponent: RootNotFound,
	head: () => ({
		meta: [
			{ charSet: "utf-8" },
			{ name: "viewport", content: "width=device-width, initial-scale=1" },
			{ title: "Oil Splitter — KH-weighted oil allocation" },
			{
				name: "description",
				content:
					"A SaaS platform for marker-based oil splitting analysis. Ingest production data, run KH-weighted allocation, and review results — all in one workspace.",
			},
		],
		links: [{ rel: "stylesheet", href: appCss }],
	}),
	shellComponent: RootDocument,
});

function Providers({ children }: { children: ReactNode }) {
	const [queryClient] = useState(
		() =>
			new QueryClient({
				defaultOptions: {
					queries: {
						staleTime: 60_000,
						retry: 1,
						refetchOnWindowFocus: false,
					},
				},
			}),
	);

	return (
		<QueryClientProvider client={queryClient}>
			<AuthProvider>{children}</AuthProvider>
		</QueryClientProvider>
	);
}

function RootDocument({ children }: { children: ReactNode }) {
	return (
		<html lang="en">
			<head>
				<HeadContent />
			</head>
			<body>
				<Providers>
					<div className="flex min-h-screen flex-col">
						<SiteHeader />
						<main className="flex-1">{children}</main>
						<SiteFooter />
					</div>
				</Providers>
				<TanStackDevtools
					config={{ position: "bottom-right" }}
					plugins={[
						{
							name: "Tanstack Router",
							render: <TanStackRouterDevtoolsPanel />,
						},
					]}
				/>
				<Scripts />
			</body>
		</html>
	);
}
