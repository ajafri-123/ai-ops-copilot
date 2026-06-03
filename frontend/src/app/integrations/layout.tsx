"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { isAuthenticated } from "@/lib/auth";

export default function IntegrationsLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
    }
  }, [router]);

  if (typeof window !== "undefined" && !isAuthenticated()) {
    return null;
  }

  return <>{children}</>;
}
