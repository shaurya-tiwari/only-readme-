import { Link } from "react-router-dom";
import { ArrowRight, Radar, ShieldCheck, Wallet } from "lucide-react";

import { useAuth } from "../auth/AuthContext";
import SectionHeader from "../components/SectionHeader";

const pillars = [
  {
    icon: ShieldCheck,
    title: "Parametric coverage",
    description: "Workers buy weekly coverage once. They do not file claims when disruption hits.",
  },
  {
    icon: Radar,
    title: "Real-time trigger engine",
    description: "Rain, heat, AQI, traffic, platform outages, and civic disruption signals are processed automatically.",
  },
  {
    icon: Wallet,
    title: "Fast payout path",
    description: "Eligible claims move through fraud checks, decisions, and simulated payouts without manual worker paperwork.",
  },
];

export default function Home() {
  const { booting, isAuthenticated, role, session } = useAuth();
  const displayName = session?.session?.name || session?.session?.username || "there";

  let heroTitle = "RideShield turns raw disruption data into visible claim and payout flows.";
  let heroDescription =
    "This frontend sits on top of the completed Sprint 1 and Sprint 2 backend. It gives you onboarding, worker operations, admin review, and scenario-driven demo control in one place.";
  let primaryCta = { to: "/onboarding", label: "Start onboarding" };
  let secondaryCta = { to: "/auth", label: "Sign in" };
  let tertiaryCta = { to: "/demo", label: "Run scenarios" };

  if (!booting && isAuthenticated && role === "worker") {
    heroTitle = `Welcome back, ${displayName}. Your coverage and claim history are ready.`;
    heroDescription = "Jump straight into the worker dashboard to review policy status, grouped claim incidents, payouts, and nearby disruptions.";
    primaryCta = { to: "/dashboard", label: "Open dashboard" };
    secondaryCta = { to: "/onboarding", label: "Create another demo worker" };
    tertiaryCta = { to: "/auth", label: "Switch account" };
  } else if (!booting && isAuthenticated && role === "admin") {
    heroTitle = `Welcome back, ${displayName}. The review queue and demo controls are live.`;
    heroDescription = "Use the admin panel to monitor review pressure, then move to the demo runner when you want to generate or reset disruption scenarios.";
    primaryCta = { to: "/admin", label: "Open admin panel" };
    secondaryCta = { to: "/demo", label: "Run scenarios" };
    tertiaryCta = { to: "/auth", label: "Switch account" };
  }

  return (
    <div className="space-y-10">
      <section className="grid gap-8 lg:grid-cols-[1.2fr_0.8fr] lg:items-end">
        <div className="panel overflow-hidden p-8 sm:p-10">
          <p className="mb-3 text-xs font-semibold uppercase tracking-[0.32em] text-ink/45">Sprint 3 frontend</p>
          <h1 className="max-w-3xl text-4xl font-bold leading-tight sm:text-5xl">{heroTitle}</h1>
          <p className="mt-5 max-w-2xl text-base text-ink/70 sm:text-lg">{heroDescription}</p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link to={primaryCta.to} className="button-primary">
              {primaryCta.label}
              <ArrowRight size={18} />
            </Link>
            <Link to={secondaryCta.to} className="button-secondary">
              {secondaryCta.label}
            </Link>
            <Link to={tertiaryCta.to} className="button-secondary">
              {tertiaryCta.label}
            </Link>
          </div>
        </div>

        <div className="panel grid gap-4 p-6">
          <div className="rounded-3xl bg-ink p-5 text-white">
            <p className="text-xs uppercase tracking-[0.25em] text-white/60">System promise</p>
            <p className="mt-3 text-2xl font-bold">Claims are system-triggered, not form-triggered.</p>
          </div>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-1">
            <div className="rounded-3xl bg-forest/10 p-5">
              <p className="text-sm text-ink/55">Worker path</p>
              <p className="mt-2 font-semibold">
                {role === "worker"
                  ? "Resume the worker dashboard, check grouped incidents, and inspect payout history."
                  : "Register, buy policy, see coverage and payout history."}
              </p>
            </div>
            <div className="rounded-3xl bg-storm/10 p-5">
              <p className="text-sm text-ink/55">Admin path</p>
              <p className="mt-2 font-semibold">
                {role === "admin"
                  ? "Open the admin panel, review grouped incidents, and run new scenarios."
                  : "Sign in separately, review delayed claims, and validate event pressure."}
              </p>
            </div>
          </div>
        </div>
      </section>

      <section>
        <SectionHeader
          eyebrow="Core flow"
          title="How the backend becomes a product surface"
          description="The frontend uses the live APIs already present in the repo. The goal here is clarity: make the engine observable and demoable."
        />
        <div className="grid gap-5 md:grid-cols-3">
          {pillars.map(({ icon: Icon, title, description }) => (
            <div key={title} className="panel p-6">
              <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-black/[0.04]">
                <Icon size={22} />
              </div>
              <h3 className="mt-5 text-xl font-bold">{title}</h3>
              <p className="mt-3 text-sm text-ink/65">{description}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
