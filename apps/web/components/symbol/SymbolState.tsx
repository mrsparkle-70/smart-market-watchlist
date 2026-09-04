"use client";

export function SymbolError({ title, error, onRetry }: { title: string; error: unknown; onRetry?: () => void }) {
  const message = error instanceof Error ? error.message : "The provider returned an unexpected response.";
  return <div className="rounded-xl border border-rose-400/20 bg-rose-400/[0.06] p-4" role="alert"><div className="flex items-start gap-3"><span className="mt-0.5 grid h-6 w-6 shrink-0 place-items-center rounded-full bg-rose-400/15 text-xs text-rose-200">!</span><div className="min-w-0"><p className="text-sm font-medium text-rose-100">{title}</p><p className="mt-1 break-words text-xs leading-relaxed text-rose-200/70">{message}</p>{onRetry && <button type="button" className="mt-3 text-xs font-semibold text-rose-200 underline decoration-rose-400/40 underline-offset-4 hover:text-white" onClick={onRetry}>Try again</button>}</div></div></div>;
}

export function SymbolEmpty({ title, detail }: { title: string; detail: string }) {
  return <div className="rounded-xl border border-dashed b-line bg-slate-950/20 p-5 text-center"><p className="text-sm font-medium text-slate-300">{title}</p><p className="mx-auto mt-1 max-w-sm text-xs leading-relaxed text-slate-500">{detail}</p></div>;
}

export function SymbolSkeleton({ className = "h-20" }: { className?: string }) {
  return <div className={`skeleton ${className}`} aria-label="Loading" />;
}
