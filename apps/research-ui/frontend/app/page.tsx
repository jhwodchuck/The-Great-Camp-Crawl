"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import Link from "next/link";

export default function Home() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (user) {
      router.push("/dashboard");
    }
  }, [user, loading, router]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-gray-500 text-lg">Loading…</p>
      </div>
    );
  }

  if (user) return null;

  return (
    <div className="min-h-screen bg-gradient-to-b from-green-50 to-white flex flex-col items-center justify-center px-4 py-16">
      <div className="max-w-2xl w-full text-center space-y-6">
        <h1 className="text-4xl font-bold text-gray-900">🏕️ The Great Camp Crawl</h1>
        <p className="text-lg text-gray-600">
          Breadth-first overnight camp research across the US, Canada, and Mexico.
          Over 350 venue-level dossiers covering traditional camps, specialty programs,
          arts &amp; music camps, and college pre-college residential programs.
        </p>

        <a
          href="https://jhwodchuck.github.io/The-Great-Camp-Crawl/"
          className="inline-block bg-green-600 hover:bg-green-700 text-white font-semibold px-8 py-3 rounded-xl shadow transition-colors"
        >
          Browse the Camp Catalog →
        </a>

        <p className="text-sm text-gray-400 pt-4">
          Research contributor?{" "}
          <Link href="/login" className="text-green-700 hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}


