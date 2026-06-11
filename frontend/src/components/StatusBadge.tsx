import { clsx } from "clsx";

interface Props { status: string; }

const colorMap: Record<string, string> = {
  ok:       "bg-green-500/15 text-green-400 border-green-500/25",
  degraded: "bg-amber-500/15 text-amber-400 border-amber-500/25",
  error:    "bg-red-500/15 text-red-400 border-red-500/25",
};

export function StatusBadge({ status }: Props) {
  return (
    <span className={clsx(
      "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wide",
      colorMap[status] ?? colorMap.error,
    )}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {status}
    </span>
  );
}
