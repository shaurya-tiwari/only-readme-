import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";

import { useAuth } from "../auth/AuthContext";
import PlanCard from "../components/PlanCard";
import PremiumCalculator from "../components/PremiumCalculator";
import RiskGauge from "../components/RiskGauge";
import SectionHeader from "../components/SectionHeader";
import { locationsApi } from "../api/locations";
import { policiesApi } from "../api/policies";
import { workersApi } from "../api/workers";
import { PLATFORM_OPTIONS, STORAGE_KEYS } from "../utils/constants";

const initialForm = {
  name: "",
  phone: "",
  city: "delhi",
  zone: "south_delhi",
  platform: "zomato",
  self_reported_income: 900,
  working_hours: 9,
  consent_given: false,
};

export default function Onboarding() {
  const navigate = useNavigate();
  const { loginWorker } = useAuth();
  const [step, setStep] = useState("register");
  const [form, setForm] = useState(initialForm);
  const [loading, setLoading] = useState(false);
  const [locationsLoading, setLocationsLoading] = useState(true);
  const [cityOptions, setCityOptions] = useState([]);
  const [zoneOptions, setZoneOptions] = useState([]);
  const [registration, setRegistration] = useState(null);
  const [selectedPlan, setSelectedPlan] = useState("");
  const [policyPurchase, setPolicyPurchase] = useState(null);
  const selectedPlanData = registration?.available_plans?.find((plan) => plan.plan_name === selectedPlan);

  useEffect(() => {
    loadCities();
  }, []);

  useEffect(() => {
    if (form.city) {
      loadZones(form.city);
    }
  }, [form.city]);

  async function loadCities() {
    setLocationsLoading(true);
    try {
      const response = await locationsApi.cities();
      const cities = response.data || [];
      setCityOptions(cities);
      if (cities.length && !cities.some((city) => city.slug === form.city)) {
        setForm((current) => ({ ...current, city: cities[0].slug }));
      }
    } finally {
      setLocationsLoading(false);
    }
  }

  async function loadZones(citySlug) {
    const response = await locationsApi.zones(citySlug);
    const zones = response.data || [];
    setZoneOptions(zones);
    if (zones.length && !zones.some((zone) => zone.slug === form.zone)) {
      setForm((current) => ({ ...current, zone: zones[0].slug }));
    }
  }

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function handleRegister(event) {
    event.preventDefault();
    setLoading(true);
    try {
      const response = await workersApi.register({
        ...form,
        self_reported_income: Number(form.self_reported_income),
        working_hours: Number(form.working_hours),
      });
      setRegistration(response.data);
      setSelectedPlan(response.data.recommended_plan);
      localStorage.setItem(STORAGE_KEYS.workerId, response.data.worker_id);
      await loginWorker(form.phone);
      setStep("plan");
      toast.success("Worker registered");
    } finally {
      setLoading(false);
    }
  }

  async function handlePurchase() {
    if (!selectedPlan) {
      toast.error("Select a plan before continuing");
      return;
    }
    setLoading(true);
    try {
      const response = await policiesApi.create({
        worker_id: registration.worker_id,
        plan_name: selectedPlan,
      });
      setPolicyPurchase(response.data);
      setStep("complete");
      toast.success("Policy purchased");
    } finally {
      setLoading(false);
    }
  }

  if (step === "complete" && registration && policyPurchase) {
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <SectionHeader
          eyebrow="Ready"
          title="Worker onboarding completed"
          description="The worker profile is registered, the policy is created, and the session is ready for dashboard access."
        />
        <div className="panel p-8">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-3xl bg-black/[0.03] p-5">
              <p className="text-sm text-ink/55">Worker</p>
              <p className="mt-2 text-2xl font-bold">{registration.name}</p>
              <p className="mt-2 text-sm text-ink/60">{registration.city} · {registration.zone} · {registration.platform}</p>
            </div>
            <div className="rounded-3xl bg-forest/10 p-5">
              <p className="text-sm text-ink/55">Policy</p>
              <p className="mt-2 text-2xl font-bold">{policyPurchase.policy.plan_display_name}</p>
              <p className="mt-2 text-sm text-ink/60">{policyPurchase.message}</p>
            </div>
          </div>
          <div className="mt-6 flex flex-wrap gap-3">
            <button type="button" className="button-primary" onClick={() => navigate("/dashboard")}>
              Open worker dashboard
            </button>
            <button type="button" className="button-secondary" onClick={() => navigate("/auth")}>
              Sign in again later
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-5xl space-y-8">
      <SectionHeader
        eyebrow="Worker onboarding"
        title="Register a delivery worker and buy a policy"
        description="This flow uses the real worker registration and policy purchase APIs. Admin-only simulation actions stay outside the worker signup flow."
      />

      {step === "register" ? (
        <div className="grid gap-6 lg:grid-cols-[0.95fr_1.05fr]">
          <form className="panel p-6" onSubmit={handleRegister}>
            <div className="grid gap-5">
              <div>
                <label className="label">Full name</label>
                <input className="field" value={form.name} onChange={(e) => updateField("name", e.target.value)} required />
              </div>
              <div>
                <label className="label">Phone number</label>
                <input className="field" value={form.phone} onChange={(e) => updateField("phone", e.target.value)} required />
              </div>
              <div className="grid gap-5 sm:grid-cols-2">
                <div>
                  <label className="label">City</label>
                  <select className="field" value={form.city} onChange={(e) => updateField("city", e.target.value)} disabled={locationsLoading}>
                    {cityOptions.map((option) => (
                      <option key={option.id} value={option.slug}>
                        {option.display_name}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="label">Zone</label>
                  <select className="field" value={form.zone} onChange={(e) => updateField("zone", e.target.value)} disabled={locationsLoading || !zoneOptions.length}>
                    {zoneOptions.map((zone) => (
                      <option key={zone.id} value={zone.slug}>
                        {zone.display_name}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="grid gap-5 sm:grid-cols-2">
                <div>
                  <label className="label">Platform</label>
                  <select className="field" value={form.platform} onChange={(e) => updateField("platform", e.target.value)}>
                    {PLATFORM_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="label">Working hours per day</label>
                  <input className="field" type="number" step="0.5" value={form.working_hours} onChange={(e) => updateField("working_hours", e.target.value)} />
                </div>
              </div>
              <div>
                <label className="label">Self-reported daily income</label>
                <input className="field" type="number" value={form.self_reported_income} onChange={(e) => updateField("self_reported_income", e.target.value)} />
              </div>
              <label className="flex items-start gap-3 rounded-2xl bg-black/[0.03] p-4 text-sm text-ink/70">
                <input
                  className="mt-1"
                  type="checkbox"
                  checked={form.consent_given}
                  onChange={(e) => updateField("consent_given", e.target.checked)}
                />
                <span>Worker consents to location, behavior, and device data being used for claim validation and fraud checks.</span>
              </label>
              <button type="submit" className="button-primary" disabled={loading || locationsLoading || !form.consent_given || !form.zone}>
                {loading ? "Calculating risk profile..." : "Register worker"}
              </button>
            </div>
          </form>

          <RiskGauge score={registration?.risk_score} breakdown={registration?.risk_breakdown} />
        </div>
      ) : null}

      {step === "plan" && registration ? (
        <div className="space-y-6">
          <RiskGauge score={registration.risk_score} breakdown={registration.risk_breakdown} />
          <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
            <div className="grid gap-4">
              {registration.available_plans.map((plan) => (
                <PlanCard key={plan.plan_name} plan={plan} selected={selectedPlan === plan.plan_name} onSelect={setSelectedPlan} />
              ))}
            </div>
            <PremiumCalculator selectedPlan={selectedPlanData} />
          </div>
          <div className="panel flex flex-col gap-4 p-6 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-sm text-ink/65">
              Coverage stays pending until the waiting period ends or an admin activates it in simulation mode. This keeps worker and admin responsibilities separate.
            </p>
            <button type="button" className="button-primary" disabled={loading} onClick={handlePurchase}>
              {loading ? "Purchasing..." : "Purchase selected plan"}
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
