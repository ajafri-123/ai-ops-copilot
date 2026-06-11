"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { clearAuth, isAuthenticated } from "@/lib/auth";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();

  useEffect(() => {
    if (!isAuthenticated()) {
      router.replace("/login");
    }
  }, [router]);

  return <>{children}</>;
}

export function useLogout() {
  const router = useRouter();
  return () => {
    clearAuth();
    router.push("/login");
  };
}
