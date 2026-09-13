"use client";

import Image from "next/image";
import Link from "next/link";
import { useAuth } from "@/lib/auth";

export default function NavBar() {
  const { user, logout } = useAuth();

  return (
    <nav className="bg-blue-600 text-white px-6 py-3 flex items-center gap-6 shadow-md">
      <Link href="/dashboard" className="flex items-center gap-3 hover:opacity-95">
        <Image src="/logo.svg" alt="The Great Camp Crawl" width={128} height={32} className="h-8 w-auto" />
        <span className="sr-only">The Great Camp Crawl</span>
      </Link>

      {user && (
        <>
          <Link href="/camps" className="hover:underline text-sm">
            Catalog
          </Link>

          <Link href="/plans" className="hover:underline text-sm">
            Summer Plans
          </Link>

          <Link href="/favorites" className="hover:underline text-sm">
            ❤️ Favorites
          </Link>

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
