"use client";

import Link from "next/link";
import { useAuth } from "@/lib/auth";

export default function NavBar() {
  const { user, logout } = useAuth();

  return (
    <nav className="bg-blue-600 text-white px-6 py-3 flex items-center gap-6 shadow-md">
      <Link href="/dashboard" className="flex items-center gap-3 hover:opacity-95">
        <img src="/logo.svg" alt="The Great Camp Crawl" className="h-8 w-auto" />
        <span className="sr-only">The Great Camp Crawl</span>
      </Link>

      {user && (
        <>
          <Link href="/missions" className="hover:underline text-sm">
            Missions
          </Link>

          {user.role === "parent" && (
            <>
              <Link href="/review" className="hover:underline text-sm">
                Review Queue
              </Link>
              <Link href="/missions/new" className="hover:underline text-sm">
                + New Mission
              </Link>
            </>
          )}

          {user.role === "child" && (
            <Link href="/contributions" className="hover:underline text-sm">
              My Contributions
            </Link>
          )}

          <div className="ml-auto flex items-center gap-4 text-sm">
            <span className="opacity-80">
              {user.role === "parent" ? "👨‍👩‍👧" : "🧒"} {user.display_name}
            </span>
            <button
              onClick={logout}
              className="bg-white text-blue-600 px-3 py-1 rounded hover:bg-blue-50 font-medium"
            >
              Log out
            </button>
          </div>
        </>
      )}
    </nav>
  );
}
