import { clsx } from "clsx";
import type { AlertSeverity, IncidentSeverity } from "@/lib/types";
import { SEVERITY_BADGE, SEVERITY_DOT } from "@/lib/severity";

interface Props {
  severity: AlertSeverity | IncidentSeverity;
  pulse?: boolean;
  size?: "sm" | "md";
}

export function SeverityBadge({ severity, pulse = false, size = "md" }: Props) {
  return (
    <span
      className={clsx(
        "inline-flex items-center gap-1.5 rounded-full border font-semibold uppercase tracking-wide",
        size === "sm" ? "px-1.5 py-0.5 text-[9px]" : "px-2.5 py-1 text-[10px]",
        SEVERITY_BADGE[severity] ?? SEVERITY_BADGE.info,
      )}
    >
      <span
        className={clsx(
          "rounded-full flex-shrink-0",
          size === "sm" ? "h-1.5 w-1.5" : "h-2 w-2",
          SEVERITY_DOT[severity],
          pulse && severity === "critical" && "animate-pulse",
        )}
      />
      {severity}
    </span>
  );
}
