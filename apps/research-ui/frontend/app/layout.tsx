import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth";
import NavBar from "@/components/NavBar";

export const metadata: Metadata = {
  title: "🏕️ The Great Camp Crawl – Research UI",
  description: "Child-friendly camp research collaboration app",
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full antialiased">
      <body className="min-h-full flex flex-col bg-gray-50 font-sans">
        <AuthProvider>
          <NavBar />
          <main className="flex-1 container mx-auto px-4 py-6 max-w-4xl">
            {children}
          </main>
        </AuthProvider>
      </body>
    </html>
  );
}
