"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { api, RegisterOptions, Role } from "@/lib/api";
import { useAuth } from "@/lib/auth";

export default function RegisterPage() {
  const { login } = useAuth();
  const router = useRouter();
  const [form, setForm] = useState({
    username: "",
    displayName: "",
    password: "",
    role: "child" as Role,
    parentInviteCode: "",
  });
  const [registerOptions, setRegisterOptions] = useState<RegisterOptions | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api.auth
      .registerOptions()
      .then(setRegisterOptions)
      .catch(() => {
        setRegisterOptions(null);
      });
  }, []);

  function update(field: string, value: string) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  const parentSignupDisabled =
    registerOptions !== null && !registerOptions.parent_self_signup_enabled;
  const parentInviteRequired =
    form.role === "parent" && !!registerOptions?.parent_invite_required;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const token = await api.auth.register(
        form.username,
        form.displayName,
        form.password,
        form.role,
        form.parentInviteCode
      );
      login(token.access_token, token.user);
      router.push("/dashboard");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="max-w-md mx-auto mt-16 bg-white rounded-2xl shadow-lg p-8">
      <div className="text-center mb-8">
        <div className="text-5xl mb-3">🏕️</div>
        <h1 className="text-2xl font-bold text-gray-800">Join the Camp Crawl!</h1>
        <p className="text-gray-500 text-sm mt-1">Create your account to start researching</p>
      </div>
      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Who are you?</label>
          <div className="flex gap-3">
            <label className={`flex-1 cursor-pointer border-2 rounded-lg p-3 text-center transition-colors ${form.role === "child" ? "border-blue-500 bg-blue-50" : "border-gray-200"}`}>
              <input
                type="radio"
                name="role"
                value="child"
                checked={form.role === "child"}
                onChange={() => update("role", "child")}
                className="sr-only"
              />
              <div className="text-2xl">🧒</div>
              <div className="text-sm font-medium mt-1">I&apos;m the kid!</div>
            </label>
            <label className={`flex-1 cursor-pointer border-2 rounded-lg p-3 text-center transition-colors ${form.role === "parent" ? "border-blue-500 bg-blue-50" : "border-gray-200"}`}>
              <input
                type="radio"
                name="role"
                value="parent"
                checked={form.role === "parent"}
                onChange={() => update("role", "parent")}
                disabled={parentSignupDisabled}
                className="sr-only"
              />
              <div className="text-2xl">👨‍👩‍👧</div>
              <div className="text-sm font-medium mt-1">I&apos;m the parent</div>
            </label>
          </div>
          {registerOptions?.message && (
            <p className="mt-2 text-xs text-gray-500">{registerOptions.message}</p>
          )}
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Display Name</label>
          <input
            type="text"
            value={form.displayName}
            onChange={(e) => update("displayName", e.target.value)}
            required
            className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
            placeholder="e.g. Sam or Dad"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
          <input
            type="text"
            value={form.username}
            onChange={(e) => update("username", e.target.value)}
            required
            className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
            placeholder="e.g. sam2024"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
          <input
            type="password"
            value={form.password}
            onChange={(e) => update("password", e.target.value)}
            required
            minLength={6}
            className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
            placeholder="••••••••"
          />
        </div>
        {parentInviteRequired && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Parent Invite Code
            </label>
            <input
              type="password"
              value={form.parentInviteCode}
              onChange={(e) => update("parentInviteCode", e.target.value)}
              required
              className="w-full border border-gray-300 rounded-lg px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-400"
              placeholder="Invite code from deployment settings"
            />
          </div>
        )}
        {error && <p className="text-red-500 text-sm">{error}</p>}
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-600 text-white py-2 rounded-lg font-semibold hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "Creating account…" : "Create Account"}
        </button>
      </form>
      <p className="text-center text-sm text-gray-500 mt-6">
        Already have an account?{" "}
        <Link href="/login" className="text-blue-600 hover:underline font-medium">
          Sign in
        </Link>
      </p>
    </div>
  );
}
