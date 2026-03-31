import { useMemo, useState } from "react";
import { NavLink, useLocation, useNavigate } from "react-router-dom";
import { Bell, BrainCircuit, LayoutDashboard, LogOut, PlaySquare, Search, Settings, Shield, ShieldCheck, Siren, Sparkles } from "lucide-react";

import { useAuth } from "../auth/AuthContext";

const workerNav = [
  { to: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
];

const adminNav = [
  { to: "/admin", label: "Admin Panel", icon: ShieldCheck },
  { to: "/demo", label: "Demo Runner", icon: PlaySquare },
  { to: "/intelligence", label: "Intelligence", icon: BrainCircuit },
];

export default function AppFrame({ children }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { session, role, logout } = useAuth();
  const [searchValue, setSearchValue] = useState("");

  const navItems = role === "admin" ? adminNav : workerNav;
  const title =
    location.pathname.startsWith("/demo")
      ? "Simulation Control"
      : location.pathname.startsWith("/intelligence")
        ? "System Intelligence"
      : location.pathname.startsWith("/admin")
        ? "System Oversight"
        : "Worker Dashboard";
  const userLabel = session?.session?.name || session?.session?.username || "RideShield user";
  const searchPlaceholder = role === "admin" ? "Search claims, zones, or reviews..." : "Search incidents or payouts...";
  const initials = useMemo(
    () =>
      userLabel
        .split(" ")
        .slice(0, 2)
        .map((part) => part[0]?.toUpperCase())
        .join("") || "RS",
    [userLabel],
  );

  async function handleLogout() {
    await logout();
    navigate("/auth");
  }

  return (
    <div className="min-h-screen">
      <aside className="fixed inset-y-0 left-0 z-40 hidden w-64 flex-col bg-surface lg:flex">
        <div className="flex h-full flex-col p-6">
          <div className="mb-8 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-[16px] bg-[linear-gradient(135deg,#003535_0%,#0d4d4d_100%)] text-on-primary">
              <Shield size={18} />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.28em] text-on-surface-variant">RideShield</p>
              <p className="text-base font-bold text-primary whitespace-nowrap">Parametric protection</p>
            </div>
          </div>

          <button type="button" className="button-primary mb-6 w-full justify-start rounded-[22px] px-4 py-3">
            <Sparkles size={16} />
            {role === "admin" ? "Review live incidents" : "View active protection"}
          </button>

          <nav className="space-y-1">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-[18px] px-4 py-3 text-sm font-semibold transition ${
                    isActive ? "bg-surface-container-lowest text-primary shadow-[0_10px_30px_rgba(26,28,25,0.06)]" : "text-on-surface-variant hover:bg-surface-container-low"
                  }`
                }
              >
                <item.icon size={17} />
                <span>{item.label}</span>
              </NavLink>
            ))}
          </nav>

          <div className="mt-auto space-y-2 border-t border-black/5 pt-6">
            <div className="rounded-[24px] bg-surface-container-lowest p-4 shadow-[0_12px_30px_rgba(26,28,25,0.05)]">
              <div className="flex items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary-container text-sm font-bold text-on-primary">
                  {initials}
                </div>
                <div>
                  <p className="text-sm font-semibold text-primary">{userLabel}</p>
                  <p className="text-xs text-on-surface-variant">{role === "admin" ? "Operations session" : "Protected worker session"}</p>
                </div>
              </div>
              <div className="mt-4 flex items-center gap-2 text-sm font-medium text-emerald-800">
                <Sparkles size={15} />
                <span>{role === "admin" ? "Live oversight enabled" : "Automatic protection active"}</span>
              </div>
            </div>

            <button type="button" className="flex w-full items-center gap-3 rounded-[18px] px-4 py-3 text-sm font-semibold text-on-surface-variant transition hover:bg-surface-container-low" onClick={handleLogout}>
              <LogOut size={16} />
              Sign out
            </button>
            <button type="button" className="flex w-full items-center gap-3 rounded-[18px] px-4 py-3 text-sm font-semibold text-on-surface-variant transition hover:bg-surface-container-low">
              <Settings size={16} />
              Settings
            </button>
          </div>
        </div>
      </aside>

      <main className="min-h-screen lg:ml-64">
        <header className="sticky top-0 z-30 border-b border-black/5 bg-surface-container-lowest/85 backdrop-blur-xl">
          <div className="mx-auto flex h-16 max-w-7xl items-center justify-between gap-4 px-4 sm:px-6 lg:px-8">
            <div className="flex items-center gap-4">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.24em] text-on-surface-variant">{title}</p>
                <p className="text-sm font-bold text-primary">
                  {role === "admin" ? "Operational control surface" : "Coverage, incidents, and payouts"}
                </p>
              </div>
            </div>

            <div className="hidden items-center gap-4 md:flex">
              <div className="relative">
                <Search size={16} className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant/70" />
                <input
                  type="text"
                  value={searchValue}
                  onChange={(event) => setSearchValue(event.target.value)}
                  placeholder={searchPlaceholder}
                  className="field !w-72 !rounded-full !bg-surface-container-low !py-2 !pl-10 !pr-4 text-sm"
                />
              </div>
              <button type="button" className="button-secondary !rounded-full !bg-tertiary-container !px-4 !py-2 !text-on-primary" aria-label="Emergency alert">
                <Siren size={16} />
                Alert
              </button>
              <button type="button" aria-label="Notifications" className="rounded-full bg-surface-container-low p-3 text-on-surface-variant transition hover:bg-surface-container">
                <Bell size={16} />
              </button>
            </div>
          </div>
        </header>

        <div className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">{children}</div>
      </main>

      <nav className="fixed bottom-0 left-0 right-0 z-40 border-t border-black/5 bg-surface-container-lowest/95 px-4 py-3 backdrop-blur-xl lg:hidden">
        <div className="mx-auto flex max-w-xl items-center justify-around">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex flex-col items-center gap-1 text-[11px] font-semibold ${isActive ? "text-primary" : "text-on-surface-variant"}`
              }
            >
              <item.icon size={18} />
              <span>{item.label}</span>
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  );
}
