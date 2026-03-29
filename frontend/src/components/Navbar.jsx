import { Link, NavLink, useLocation, useNavigate } from "react-router-dom";
import { LogOut, Shield, Sparkles } from "lucide-react";

import { useAuth } from "../auth/AuthContext";

export default function Navbar({ session }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { logout } = useAuth();

  async function handleLogout() {
    await logout();
    navigate("/auth");
  }

  const navItems = session?.role === "admin"
    ? [
        { to: "/demo", label: "Demo Runner" },
        { to: "/admin", label: "Admin" },
      ]
    : [
        { to: "/onboarding", label: "Onboarding" },
        ...(session?.role === "worker" ? [{ to: "/dashboard", label: "Dashboard" }] : []),
      ];

  return (
    <header className="sticky top-0 z-20 mb-8 pt-5">
      <div className="panel-muted flex items-center justify-between px-5 py-4">
        <Link to="/" className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-ink text-white">
            <Shield size={20} />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.3em] text-ink/50">RideShield</p>
            <p className="font-['Space_Grotesk'] text-lg font-bold">Income protection engine</p>
          </div>
        </Link>

        <nav className="hidden items-center gap-2 md:flex">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `rounded-2xl px-4 py-2 text-sm font-semibold transition ${
                  isActive ? "bg-ink text-white" : "text-ink/70 hover:bg-black/[0.04]"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="hidden items-center gap-3 lg:flex">
          <div className="items-center gap-2 rounded-full bg-emerald-50 px-3 py-2 text-sm font-medium text-emerald-700 lg:flex">
            <Sparkles size={16} />
            <span>
              {session ? `${session.role}: ${session.name || session.username}` : location.pathname === "/" ? "Ready for Sprint 3" : "Simulation mode"}
            </span>
          </div>
          {session ? (
            <button type="button" onClick={handleLogout} className="button-secondary !rounded-xl !px-3 !py-2 text-sm">
              <LogOut size={16} />
              Sign out
            </button>
          ) : null}
        </div>
      </div>
    </header>
  );
}
