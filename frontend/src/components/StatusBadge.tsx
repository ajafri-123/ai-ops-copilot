import { clsx } from "clsx";

interface Props {
  status: string;
}

const colorMap: Record<string, string> = {
  ok: "bg-green-500/20 text-green-400 border-green-500/30",
  degraded: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  error: "bg-red-500/20 text-red-400 border-red-500/30",
};

export function StatusBadge({ status }: Props) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full border px-3 py-0.5 text-xs font-medium uppercase tracking-wide",
        colorMap[status] ?? colorMap.error
      )}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {status}
    </span>
  );
}
