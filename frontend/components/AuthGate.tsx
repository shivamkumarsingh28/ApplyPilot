"use client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { auth } from "@/lib/api";
import Shell from "./Shell";

/** Wraps every signed-in page: redirects to /login without a token and renders the app shell. */
export default function AuthGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [ready, setReady] = useState(false);
  useEffect(() => {
    if (!auth.get()) router.replace("/login");
    else setReady(true);
  }, [router]);
  if (!ready) return null;
  return <Shell>{children}</Shell>;
}
