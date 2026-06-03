"use client";

import dynamic from "next/dynamic";
import { Loader2 } from "lucide-react";
import type { ServiceGraphResponse } from "@/lib/types";

// React Flow uses browser APIs — must be loaded client-side only
const ServiceGraph = dynamic(
  () => import("./ServiceGraph").then((m) => m.ServiceGraph),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-5 w-5 animate-spin text-indigo-500/50" />
      </div>
    ),
  },
);

export function ServiceGraphLoader({ graph }: { graph: ServiceGraphResponse }) {
  return <ServiceGraph graph={graph} />;
}
