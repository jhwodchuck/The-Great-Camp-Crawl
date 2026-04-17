"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";
import { useRouter } from "next/navigation";
import { api, User } from "./api";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (token: string, user: User) => void;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  loading: true,
  login: () => {},
  logout: () => {},
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    let isActive = true;

    async function hydrateSession() {
      const token = localStorage.getItem("access_token");
      if (!token) {
        if (isActive) {
          setLoading(false);
        }
        return;
      }

      try {
        const currentUser = await api.auth.me();
        if (isActive) {
          setUser(currentUser);
        }
      } catch {
        localStorage.removeItem("access_token");
      } finally {
        if (isActive) {
          setLoading(false);
        }
      }
    }

    hydrateSession();
    return () => {
      isActive = false;
    };
  }, []);

  function login(token: string, userData: User) {
    localStorage.setItem("access_token", token);
    setUser(userData);
  }

  function logout() {
    localStorage.removeItem("access_token");
    setUser(null);
    router.push("/login");
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  return useContext(AuthContext);
}

export function useRequireAuth(role?: "parent" | "child") {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (loading) return;
    if (!user) {
      router.push("/login");
      return;
    }
    if (role && user.role !== role) {
      router.push("/dashboard");
    }
  }, [user, loading, role, router]);

  return { user, loading };
}
