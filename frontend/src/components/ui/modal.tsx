import { X } from "lucide-react";
import { type ReactNode, useEffect, useRef } from "react";
import { createPortal } from "react-dom";

import { cn } from "#/lib/utils";

type Props = {
	open: boolean;
	onClose: () => void;
	title: string;
	description?: string;
	children: ReactNode;
	footer?: ReactNode;
	size?: "sm" | "md" | "lg" | "xl";
};

const sizeClasses = {
	sm: "max-w-sm",
	md: "max-w-lg",
	lg: "max-w-2xl",
	xl: "max-w-4xl",
} satisfies Record<NonNullable<Props["size"]>, string>;

export function Modal({
	open,
	onClose,
	title,
	description,
	children,
	footer,
	size = "md",
}: Props) {
	const onCloseRef = useRef(onClose);
	onCloseRef.current = onClose;

	useEffect(() => {
		if (!open) return;
		function onKey(event: KeyboardEvent) {
			if (event.key === "Escape") onCloseRef.current();
		}
		window.addEventListener("keydown", onKey);
		// NOTE: deliberately *not* locking ``document.body.style.overflow``
		// here. Tall modals (e.g. the Excel sheet picker) need the page to
		// remain scrollable so the user can reach the modal's footer
		// buttons, and the absolute-positioned wrapper below grows with
		// page height instead of clipping at the viewport.
		return () => {
			window.removeEventListener("keydown", onKey);
		};
	}, [open]);

	if (!open) return null;
	if (typeof document === "undefined") return null;

	// Portal to ``document.body`` so ``position: fixed`` is relative to the
	// viewport regardless of any transformed/filtered ancestor in the page
	// tree. Without this the backdrop only covers the ancestor's bounding
	// box, leaving the rest of the page exposed.
	return createPortal(
		<div
			className="fixed inset-0 z-50 overflow-y-auto"
			role="dialog"
			aria-modal="true"
			aria-labelledby="modal-title"
		>
			<button
				type="button"
				aria-label="Close dialog"
				onClick={onClose}
				className="fixed inset-0 cursor-default bg-(--sea-ink)/35 backdrop-blur-sm"
			/>
			<div className="relative flex min-h-full items-start justify-center p-4 sm:p-6">
				<div
					className={cn(
						"island-shell relative z-10 my-auto flex w-full flex-col rounded-3xl",
						sizeClasses[size],
					)}
				>
					<header className="flex items-start justify-between gap-4 border-b border-(--line)/70 px-6 py-4">
						<div>
							<h2
								id="modal-title"
								className="display-title text-lg font-bold text-(--sea-ink)"
							>
								{title}
							</h2>
							{description ? (
								<p className="mt-1 text-sm text-(--sea-ink-soft)">
									{description}
								</p>
							) : null}
						</div>
						<button
							type="button"
							onClick={onClose}
							className="grid h-8 w-8 place-items-center rounded-full text-(--sea-ink-soft) transition-colors hover:bg-(--surface) hover:text-(--sea-ink)"
							aria-label="Close"
						>
							<X size={16} />
						</button>
					</header>

					<div className="px-6 py-5">{children}</div>

					{footer ? (
						<footer className="flex items-center justify-end gap-2 border-t border-(--line)/70 px-6 py-4">
							{footer}
						</footer>
					) : null}
				</div>
			</div>
		</div>,
		document.body,
	);
}
