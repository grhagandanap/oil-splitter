export function SiteFooter() {
  return (
    <footer className="site-footer mt-16 py-6">
      <div className="page-wrap flex flex-col items-center justify-between gap-2 text-xs text-(--sea-ink-soft) sm:flex-row">
        <span>
          &copy; {new Date().getFullYear()} Oil Splitter — KH-weighted oil allocation,
          made simple.
        </span>
        <span className="opacity-80">
          Built with FastAPI &middot; TanStack Start &middot; PostgreSQL
        </span>
      </div>
    </footer>
  )
}
