import { Link } from "react-router-dom";
import { ArrowRight, Radar, ShieldCheck, Wallet } from "lucide-react";

import { useAuth } from "../auth/AuthContext";
import SectionHeader from "../components/SectionHeader";

const pillars = [
  {
    icon: ShieldCheck,
    title: "Parametric coverage",
    description: "Workers buy weekly coverage once. They do not file claims when disruption hits because the system detects incidents in the background.",
  },
  {
    icon: Radar,
    title: "Incident-first monitoring",
    description: "Rain, heat, AQI, traffic, platform outages, and civic disruption signals are merged into one explainable incident instead of noisy duplicate events.",
  },
  {
    icon: Wallet,
    title: "Visible payout engine",
    description: "Eligible claims move through fraud checks, decisioning, and wallet payout simulation with a transparent system story for workers and admins.",
  },
];

export default function Home() {
  const { booting, isAuthenticated, role, session } = useAuth();
  const displayName = session?.session?.name || session?.session?.username || "there";

  let heroTitle = "RideShield turns disruption signals into trustable claim and payout decisions.";
  let heroDescription =
    "The product now connects onboarding, worker coverage, admin review, live trigger monitoring, and scenario-driven demos in one coherent operating surface.";
  let primaryCta = { to: "/onboarding", label: "Start onboarding" };
  let secondaryCta = { to: "/auth", label: "Sign in" };
  let tertiaryCta = { to: "/demo", label: "Open demo runner" };

  if (!booting && isAuthenticated && role === "worker") {
    heroTitle = `Welcome back, ${displayName}. Your RideShield coverage is already in motion.`;
    heroDescription =
      "Open the dashboard to review policy state, grouped incidents, recent payouts, and the logic behind the latest system decisions.";
    primaryCta = { to: "/dashboard", label: "Open dashboard" };
    secondaryCta = { to: "/onboarding", label: "Create another demo worker" };
    tertiaryCta = { to: "/auth", label: "Switch account" };
  } else if (!booting && isAuthenticated && role === "admin") {
    heroTitle = `Welcome back, ${displayName}. Monitoring, review, and scenario controls are live.`;
    heroDescription =
      "Move between the admin panel and demo runner to observe cause and effect from threshold breach to incident, claim, and payout.";
    primaryCta = { to: "/admin", label: "Open admin panel" };
    secondaryCta = { to: "/demo", label: "Run scenarios" };
    tertiaryCta = { to: "/auth", label: "Switch account" };
  }

  return (
    <div className="space-y-12">
      <section className="grid gap-6 xl:grid-cols-[1.15fr_0.85fr]">
        <div className="hero-glow rounded-[36px] p-8 sm:p-10">
          <p className="text-[11px] font-semibold uppercase tracking-[0.3em] text-white/60">RideShield system</p>
          <h1 className="mt-4 max-w-4xl text-4xl font-bold leading-tight sm:text-5xl">{heroTitle}</h1>
          <p className="mt-5 max-w-2xl text-base leading-8 text-white/78 sm:text-lg">{heroDescription}</p>

          <div className="mt-8 flex flex-wrap gap-3">
            <Link to={primaryCta.to} className="button-secondary !bg-white !text-[#173126]">
              {primaryCta.label}
              <ArrowRight size={18} />
            </Link>
            <Link to={secondaryCta.to} className="rounded-[20px] bg-white/10 px-5 py-3 font-semibold text-white transition hover:bg-white/15">
              {secondaryCta.label}
            </Link>
            <Link to={tertiaryCta.to} className="rounded-[20px] bg-white/10 px-5 py-3 font-semibold text-white transition hover:bg-white/15">
              {tertiaryCta.label}
            </Link>
          </div>

          <div className="mt-10 grid gap-4 sm:grid-cols-3">
            <div className="rounded-[24px] bg-white/10 p-4">
              <p className="text-[11px] uppercase tracking-[0.24em] text-white/55">Claim model</p>
              <p className="mt-2 text-lg font-semibold">Incident-first</p>
            </div>
            <div className="rounded-[24px] bg-white/10 p-4">
              <p className="text-[11px] uppercase tracking-[0.24em] text-white/55">Trigger loop</p>
              <p className="mt-2 text-lg font-semibold">Scheduler + demo override</p>
            </div>
            <div className="rounded-[24px] bg-white/10 p-4">
              <p className="text-[11px] uppercase tracking-[0.24em] text-white/55">Coverage story</p>
              <p className="mt-2 text-lg font-semibold">Zero manual filing</p>
            </div>
          </div>
        </div>

        <div className="editorial-grid">
          <div className="panel p-6">
            <p className="eyebrow">System promise</p>
            <p className="mt-3 text-2xl font-bold leading-tight text-[#173126]">
              Workers are informed. The system does the filing, scoring, and payout orchestration.
            </p>
            <p className="mt-4 text-sm leading-7 text-ink/65">
              RideShield is designed to observe disruption signals, translate them into one clear incident, and expose
              that reasoning across worker, admin, and demo views.
            </p>
          </div>

          <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-1">
            <div className="panel-quiet p-6">
              <p className="text-sm text-ink/55">Worker surface</p>
              <p className="mt-2 text-lg font-semibold text-[#173126]">
                Coverage, incidents, payout history, and decision explanations in one calm, readable view.
              </p>
            </div>
            <div className="panel-quiet p-6">
              <p className="text-sm text-ink/55">Admin surface</p>
              <p className="mt-2 text-lg font-semibold text-[#173126]">
                Review queue, disruption pressure, fraud visibility, scheduler health, and city-aware monitoring.
              </p>
            </div>
          </div>
        </div>
      </section>

      <section>
        <SectionHeader
          eyebrow="Core flow"
          title="How the backend becomes a visible product"
          description="The frontend does not mock product logic. It makes the real engine legible so workers trust outcomes and admins understand why those outcomes happened."
        />

        <div className="grid gap-5 md:grid-cols-3">
          {pillars.map(({ icon: Icon, title, description }) => (
            <div key={title} className="panel p-6">
              <div className="flex h-12 w-12 items-center justify-center rounded-[18px] bg-[#f4f4ef] text-[#173126]">
                <Icon size={22} />
              </div>
              <h3 className="mt-5 text-xl font-bold text-[#173126]">{title}</h3>
              <p className="mt-3 text-sm leading-7 text-ink/65">{description}</p>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
