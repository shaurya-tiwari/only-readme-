import { useState } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { LogOut, Menu, Shield, Sparkles, X } from "lucide-react";

import { useAuth } from "../auth/AuthContext";

export default function Navbar({ session }) {
  const navigate = useNavigate();
  const { logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  async function handleLogout() {
    await logout();
    navigate("/auth");
  }

  const navItems = session?.session?.role === "admin"
    ? [
        { to: "/intelligence", label: "Intelligence" },
        { to: "/demo", label: "Demo Runner" },
        { to: "/lab", label: "Scenario Lab" },
        { to: "/admin", label: "Admin" },
      ]
    : [
        { to: "/how-it-works", label: "How It Works" },
        { to: "/onboarding", label: "Onboarding" },
        ...(session?.session?.role === "worker" ? [{ to: "/dashboard", label: "Dashboard" }] : []),
      ];

  return (
    <header className="sticky top-0 z-20 mb-10 pt-5">
      <div className="glass-strip rounded-[30px] px-5 py-4">
        <div className="flex items-center justify-between gap-4">
          <Link to="/" className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-[18px] bg-cta-gradient text-on-primary">
              <Shield size={20} />
            </div>
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.3em] text-on-surface-variant">RideShield</p>
              <p className="text-lg font-bold text-primary">Income protection engine</p>
            </div>
          </Link>

          <nav className="hidden items-center gap-2 md:flex">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  `rounded-[18px] px-4 py-2 text-sm font-semibold transition ${
                    isActive ? "bg-primary text-on-primary" : "text-on-surface-variant hover:bg-white/[0.06]"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="hidden items-center gap-3 lg:flex">
            <div className="items-center gap-2 rounded-full px-3 py-2 text-sm font-medium lg:flex" style={{ background: "rgba(0, 53, 48, 0.4)", color: "#69f8e9" }}>
              <Sparkles size={16} />
              <span>{session?.session ? `${session.session.role}: ${session.session.name || session.session.username}` : "Monitoring ready"}</span>
            </div>
            {session ? (
              <button type="button" onClick={handleLogout} className="button-secondary !rounded-xl !px-3 !py-2 text-sm">
                <LogOut size={16} />
                Sign out
              </button>
            ) : null}
          </div>

          <button
            type="button"
            className="inline-flex h-11 w-11 items-center justify-center rounded-full bg-surface-container-high text-on-surface md:hidden"
            onClick={() => setMenuOpen((value) => !value)}
            aria-label={menuOpen ? "Close navigation" : "Open navigation"}
          >
            {menuOpen ? <X size={18} /> : <Menu size={18} />}
          </button>
        </div>

        {menuOpen ? (
          <div className="mt-4 space-y-2 border-t border-white/10 pt-4 md:hidden">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={() => setMenuOpen(false)}
                className={({ isActive }) =>
                  `block rounded-[18px] px-4 py-3 text-sm font-semibold ${isActive ? "bg-primary text-on-primary" : "text-on-surface-variant"}`
                }
              >
                {item.label}
              </NavLink>
            ))}
            {session ? (
              <button type="button" onClick={handleLogout} className="button-secondary w-full justify-start">
                <LogOut size={16} />
                Sign out
              </button>
            ) : null}
          </div>
        ) : null}
      </div>
    </header>
  );
}
