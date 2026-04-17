import { useCallback, useEffect, useMemo, useState } from "react";
import clsx from "clsx";
import { useNavigate } from "react-router-dom";
import toast from "react-hot-toast";

import { useTranslation } from "react-i18next";

import { useAuth } from "../auth/AuthContext";
import { locationsApi } from "../api/locations";
import { policiesApi } from "../api/policies";
import { workersApi } from "../api/workers";
import ErrorState from "../components/ErrorState";
import PlanCard from "../components/PlanCard";
import RiskGauge from "../components/RiskGauge";
import SectionHeader from "../components/SectionHeader";
import { PLATFORM_OPTIONS, STORAGE_KEYS } from "../utils/constants";
import {
  formatCurrency,
  humanizeSlug,
  ensureArray,
} from "../utils/formatters";
import { getDeviceFingerprint } from "../utils/fingerprint";

const initialForm = {
  name: "",
  phone: "",
  password: "",
  confirm_password: "",
  city: "delhi",
  zone: "south_delhi",
  platform: "zomato",
  self_reported_income: 900,
  working_hours: 9,
  consent_given: false,
};

const steps = [
  { id: "register", label: "Worker profile" },
  { id: "plan", label: "Policy choice" },
  { id: "complete", label: "Ready" },
];



function getFeaturedPlans(plans, selectedPlan, recommendedPlan) {
  const safePlans = Array.isArray(plans) ? plans : [];
  const planMap = new Map(safePlans.map((plan) => [plan.plan_name, plan]));
  const premiumChoice = ["assured_plan", "pro_max"].includes(selectedPlan)
    ? selectedPlan
    : ["assured_plan", "pro_max"].includes(recommendedPlan)
      ? recommendedPlan
      : planMap.has("pro_max")
        ? "pro_max"
        : planMap.has("assured_plan")
          ? "assured_plan"
          : null;

  const orderedNames = [
    "basic_protect",
    "smart_protect",
    premiumChoice,
    selectedPlan,
    recommendedPlan,
  ];

  return Array.from(new Set(orderedNames.filter(Boolean)))
    .map((planName) => planMap.get(planName))
    .filter(Boolean)
    .slice(0, 3);
}

function validateRegistration(form) {
  const errors = {};
  const normalizedPhone = String(form.phone || "").trim();

  if (!String(form.name || "").trim()) {
    errors.name = "auth.errors.name_required";
  }

  if (!normalizedPhone) {
    errors.phone = "auth.errors.phone_required";
  } else if (!/^\+?\d{10,15}$/.test(normalizedPhone)) {
    errors.phone = "auth.errors.phone_invalid";
  }

  if (!form.password) {
    errors.password = "auth.errors.password_required";
  } else if (String(form.password).length < 8) {
    errors.password = "auth.errors.password_length";
  }

  if (!form.confirm_password) {
    errors.confirm_password = "auth.errors.confirm_password_required";
  } else if (form.password !== form.confirm_password) {
    errors.confirm_password = "auth.errors.passwords_mismatch";
  }

  if (!form.zone) {
    errors.zone = "auth.errors.zone_required";
  }

  if (!form.consent_given) {
    errors.consent_given = "auth.errors.consent_required";
  }

  return errors;
}

function getPasswordStrength(password) {
  if (!password) {
    return null;
  }

  let score = 0;
  if (password.length >= 8) score += 1;
  if (/[A-Z]/.test(password) && /[a-z]/.test(password)) score += 1;
  if (/\d/.test(password)) score += 1;
  if (/[^A-Za-z0-9]/.test(password)) score += 1;

  if (score >= 4) {
    return { label: "auth.password.strong", tone: "text-emerald-700" };
  }
  if (score >= 2) {
    return { label: "auth.password.decent", tone: "text-amber-700" };
  }
  return { label: "auth.password.weak", tone: "text-rose-700" };
}

export default function Onboarding() {
  const { t } = useTranslation();
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
  const [planCatalog, setPlanCatalog] = useState([]);
  const [planCatalogLoading, setPlanCatalogLoading] = useState(false);
  const [planCatalogError, setPlanCatalogError] = useState("");
  const [planCatalogReloadKey, setPlanCatalogReloadKey] = useState(0);
  const [policyPurchase, setPolicyPurchase] = useState(null);
  const [draftLoaded, setDraftLoaded] = useState(false);
  const [locationsError, setLocationsError] = useState("");
  const [touched, setTouched] = useState({});
  const [showAllPlans, setShowAllPlans] = useState(false);

  const planOptions = useMemo(() => {
    const safeCatalog = Array.isArray(planCatalog) ? planCatalog : [];
    return safeCatalog.length ? safeCatalog : (Array.isArray(registration?.available_plans) ? registration.available_plans : []);
  }, [planCatalog, registration?.available_plans]);

  const safePlanOptions = useMemo(() => {
    return Array.isArray(planOptions) ? planOptions : [];
  }, [planOptions]);

  const recommendedPlanName = useMemo(() => {
    return (
      safePlanOptions.find((plan) => plan.is_recommended)?.plan_name ||
      registration?.recommended_plan ||
      ""
    );
  }, [safePlanOptions, registration?.recommended_plan]);

  const selectedPlanData = useMemo(() => {
    return (
      safePlanOptions.find((plan) => plan.plan_name === selectedPlan) ||
      (Array.isArray(registration?.available_plans) ? registration.available_plans : []).find(
        (plan) => plan.plan_name === selectedPlan,
      )
    );
  }, [safePlanOptions, selectedPlan, registration?.available_plans]);

  const featuredPlans = useMemo(
    () => getFeaturedPlans(safePlanOptions, selectedPlan, recommendedPlanName),
    [safePlanOptions, selectedPlan, recommendedPlanName],
  );

  const additionalPlans = useMemo(() => {
    const safeFeatured = Array.isArray(featuredPlans) ? featuredPlans : [];
    return safePlanOptions.filter(
      (plan) =>
        !safeFeatured.some(
          (featuredPlan) => featuredPlan.plan_name === plan.plan_name,
        ),
    );
  }, [safePlanOptions, featuredPlans]);
  const stepIndex = steps.findIndex((item) => item.id === step);
  const progressWidth = `${((stepIndex + 1) / steps.length) * 100}%`;
  const validationErrors = useMemo(() => validateRegistration(form), [form]);
  const passwordStrength = useMemo(
    () => getPasswordStrength(form.password),
    [form.password],
  );
  const monitoredCities = cityOptions.length || 4;

  useEffect(() => {
    document.title = "Onboarding | RideShield";
  }, []);

  useEffect(() => {
    try {
      const rawDraft = window.sessionStorage.getItem(
        STORAGE_KEYS.onboardingDraft,
      );
      if (rawDraft) {
        const draft = JSON.parse(rawDraft);
        if (draft.form) {
          setForm((current) => ({ ...current, ...draft.form }));
        }
        if (draft.registration) {
          setRegistration(draft.registration);
        }
        if (draft.selectedPlan) {
          setSelectedPlan(draft.selectedPlan);
        }
        if (Array.isArray(draft.planCatalog)) {
          setPlanCatalog(draft.planCatalog);
        }
        if (draft.step && draft.step !== "complete") {
          setStep(draft.step);
        }
      }
    } catch {
      window.sessionStorage.removeItem(STORAGE_KEYS.onboardingDraft);
    } finally {
      setDraftLoaded(true);
    }
  }, []);

  const loadCities = useCallback(async () => {
    setLocationsLoading(true);
    setLocationsError("");
    try {
      const response = await locationsApi.cities();
      const cities = ensureArray(response.data, "city_options");
      setCityOptions(cities);
      if (cities.length) {
        setForm((current) =>
          cities.some((city) => city.slug === current.city)
            ? current
            : { ...current, city: cities[0].slug },
        );
      }
    } catch {
      setLocationsError(t("onboarding.errors.locations"));
    } finally {
      setLocationsLoading(false);
    }
  }, [t]);

  const loadZones = useCallback(async (citySlug) => {
    try {
      setLocationsError("");
      const response = await locationsApi.zones(citySlug);
      const zones = ensureArray(response.data, `zones_${citySlug}`);
      setZoneOptions(zones);
      if (zones.length) {
        setForm((current) =>
          zones.some((zone) => zone.slug === current.zone)
            ? current
            : { ...current, zone: zones[0].slug },
        );
      }
    } catch {
      setLocationsError(t("onboarding.errors.zones"));
    }
  }, [t]);

  useEffect(() => {
    if (!draftLoaded) {
      return;
    }
    loadCities();
  }, [draftLoaded, loadCities]);

  useEffect(() => {
    if (draftLoaded && form.city) {
      loadZones(form.city);
    }
  }, [draftLoaded, form.city, loadZones]);

  useEffect(() => {
    if (!draftLoaded) {
      return;
    }
    if (step === "complete") {
      window.sessionStorage.removeItem(STORAGE_KEYS.onboardingDraft);
      return;
    }
    window.sessionStorage.setItem(
      STORAGE_KEYS.onboardingDraft,
      JSON.stringify({
        step,
        form,
        registration,
        selectedPlan,
        planCatalog,
      }),
    );
  }, [draftLoaded, form, planCatalog, registration, selectedPlan, step]);

  useEffect(() => {
    if (
      Array.isArray(additionalPlans) &&
      additionalPlans.some((plan) => plan.plan_name === selectedPlan) &&
      !showAllPlans
    ) {
      setShowAllPlans(true);
    }
  }, [additionalPlans, selectedPlan, showAllPlans]);

  useEffect(() => {
    let active = true;

    async function loadPlanCatalog() {
      if (step !== "plan" || !registration?.worker_id) {
        return;
      }

      setPlanCatalogLoading(true);
      setPlanCatalogError("");
      try {
        const response = await policiesApi.plans(registration.worker_id);
        if (!active) {
          return;
        }
        const plans = ensureArray(response.data?.plans, "plan_catalog");
        setPlanCatalog(plans);

        const recommended = response.data?.recommended;
        if (recommended) {
          setSelectedPlan((current) => {
            if (!current) {
              return recommended;
            }
            return plans.some((plan) => plan.plan_name === current)
              ? current
              : recommended;
          });
        }
      } catch (error) {
        if (!active) {
          return;
        }
        setPlanCatalogError(
          error.response?.data?.detail ||
          t("onboarding.errors.plan_catalog"),
        );
      } finally {
        if (active) {
          setPlanCatalogLoading(false);
        }
      }
    }

    loadPlanCatalog();

    return () => {
      active = false;
    };
  }, [planCatalogReloadKey, registration?.worker_id, step, t]);

  function updateField(field, value) {
    setForm((current) => ({ ...current, [field]: value }));
  }

  function markTouched(field) {
    setTouched((current) => ({ ...current, [field]: true }));
  }

  async function handleRegister(event) {
    event.preventDefault();
    const nextTouched = {
      name: true,
      phone: true,
      password: true,
      confirm_password: true,
      zone: true,
      consent_given: true,
    };
    setTouched((current) => ({ ...current, ...nextTouched }));
    if (Object.keys(validationErrors).length) {
      toast.error(t("onboarding.errors.fix_fields"));
      return;
    }
    setLoading(true);
    try {
      const response = await workersApi.register({
        password: form.password,
        name: form.name,
        phone: form.phone,
        city: form.city,
        zone: form.zone,
        platform: form.platform,
        self_reported_income: Number(form.self_reported_income),
        working_hours: Number(form.working_hours),
        consent_given: form.consent_given,
        device_fingerprint: getDeviceFingerprint(),
      });
      setRegistration(response.data);
      setPlanCatalog([]);
      setPlanCatalogError("");
      setSelectedPlan(response.data.recommended_plan);
      setStep("plan");
      toast.success(t("onboarding.errors.register_success"));
    } catch (error) {
      toast.error(
        error.response?.data?.detail || t("onboarding.errors.register_failed"),
      );
    } finally {
      setLoading(false);
    }
  }

  async function handlePurchase() {
    if (!selectedPlan) {
      toast.error(t("onboarding.errors.select_plan"));
      return;
    }
    setLoading(true);
    try {
      await policiesApi.create({
        worker_id: registration.worker_id,
        plan_name: selectedPlan,
      });
      await loginWorker(form.phone, form.password);
      setPolicyPurchase({ plan: { plan_display_name: selectedPlan } });
      setStep("complete");
      window.sessionStorage.removeItem(STORAGE_KEYS.onboardingDraft);
      toast.success(t("onboarding.errors.purchase_success"));
    } catch (error) {
      toast.error(error.response?.data?.detail || t("onboarding.errors.purchase_failed"));
    } finally {
      setLoading(false);
    }
  }

  const summaryLine = useMemo(() => {
    return `${humanizeSlug(form.city)} - ${humanizeSlug(form.zone)} - ${humanizeSlug(form.platform)}`;
  }, [form.city, form.zone, form.platform]);

  useEffect(() => {
    if (step === "complete" && registration?.worker_id) {
      const timer = setTimeout(() => {
        navigate(`/dashboard/${registration.worker_id}`);
      }, 1200);
      return () => clearTimeout(timer);
    }
  }, [step, registration?.worker_id, navigate]);

  if (step === "complete" && registration && policyPurchase) {
    return (
      <div className="mx-auto max-w-3xl space-y-6">
        <SectionHeader
          eyebrow={t("onboarding.complete.eyebrow")}
          title={t("onboarding.complete.title")}
          description={t("onboarding.complete.desc")}
        />
        <div className="decision-panel p-8">
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-3xl bg-surface-container-high border border-surface-container-highest p-5">
              <p className="text-sm font-semibold uppercase tracking-widest text-on-surface-variant">{t("onboarding.complete.worker")}</p>
              <p className="mt-2 text-2xl font-bold">{registration.name}</p>
              <p className="mt-2 text-sm text-primary">
                {t("onboarding.complete.active", { city: humanizeSlug(registration.city) })}
              </p>
            </div>
            <div className="rounded-3xl bg-surface-container-high border border-surface-container-highest p-5">
              <p className="text-sm font-semibold uppercase tracking-widest text-on-surface-variant">{t("onboarding.complete.policy")}</p>
              <p className="mt-2 text-2xl font-bold">
                {policyPurchase.plan.plan_display_name}
              </p>
              <p className="mt-2 text-sm text-primary">
                {t("onboarding.complete.premium", { amount: formatCurrency(selectedPlanData?.weekly_premium) })}
              </p>
            </div>
          </div>
          <div className="mt-6 flex flex-wrap gap-3">
            <button
              type="button"
              className="button-primary"
              disabled={loading}
              onClick={() => navigate(`/dashboard/${registration.worker_id}`)}
            >
              {t("onboarding.complete.open_dashboard")}
            </button>
            <button
              type="button"
              className="button-secondary"
              onClick={() => navigate("/auth")}
            >
              {t("onboarding.complete.sign_later")}
            </button>
          </div>
          <p className="mt-6 text-sm text-on-surface-variant text-center">
            {t("onboarding.complete.footer")}
          </p>
        </div>
      </div>
    );
  }

  return (
    <div
      className={clsx(
        "mx-auto max-w-5xl space-y-8",
        step === "plan" ? "pb-36" : "",
      )}
    >
      <SectionHeader
        eyebrow={t("onboarding.header.eyebrow")}
        title={t("onboarding.header.title")}
        description={t("onboarding.header.desc")}
      />

      <div className="context-panel p-6">
        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
          <div className="flex-1 w-full max-w-3xl">
            <div className="flex gap-2 sm:gap-3 w-full">
              {steps.map((item, index) => (
                <div
                  key={item.id}
                  className={`pill flex-1 flex items-center justify-center text-center text-xs sm:text-sm font-semibold transition-colors duration-300 ${index <= stepIndex ? "bg-primary text-white shadow-md shadow-primary/20" : "bg-surface-container-low text-on-surface-variant hover:bg-surface-container"}`}
                >
                  {t(`onboarding.steps.${item.id}`)}
                </div>
              ))}
            </div>
            <div className="mt-4 h-2 w-full overflow-hidden rounded-full bg-surface-container-low">
              <div
                className="h-full rounded-full transition-all duration-700 ease-out"
                style={{ width: progressWidth, background: "var(--rs-accent)" }}
              />
            </div>
          </div>
          {form.city && form.platform ? (
            <div className="shrink-0 lg:text-right hidden sm:block">
              <p className="text-sm font-bold uppercase tracking-widest text-on-surface-variant mb-1">{t("onboarding.form.identity")}</p>
              <p className="text-[13px] font-medium text-on-surface-variant opacity-80">{summaryLine}</p>
            </div>
          ) : null}
        </div>
      </div>

      {step === "register" ? (
        <div className="grid gap-6 lg:grid-cols-[0.95fr_1.05fr]">
          <form className="context-panel p-6" onSubmit={handleRegister}>
            <div className="space-y-6">
              {locationsError ? (
                <ErrorState message={locationsError} onRetry={loadCities} />
              ) : null}
              <div>
                <p className="eyebrow">{t("onboarding.form.identity")}</p>
                <div className="mt-4 grid gap-5">
                  <div>
                    <label className="label" htmlFor="worker-name">
                      {t("onboarding.form.name")}
                    </label>
                    <input
                      id="worker-name"
                      className="field"
                      value={form.name}
                      onBlur={() => markTouched("name")}
                      onChange={(e) => updateField("name", e.target.value)}
                      required
                    />
                    {touched.name && validationErrors.name ? (
                      <p className="mt-2 text-sm text-rose-700">
                        {t(validationErrors.name)}
                      </p>
                    ) : null}
                  </div>
                  <div>
                    <label className="label" htmlFor="worker-phone">
                      {t("onboarding.form.phone")}
                    </label>
                    <input
                      id="worker-phone"
                      className="field"
                      value={form.phone}
                      onBlur={() => markTouched("phone")}
                      onChange={(e) => updateField("phone", e.target.value)}
                      required
                    />
                    {touched.phone && validationErrors.phone ? (
                      <p className="mt-2 text-sm text-rose-700">
                        {t(validationErrors.phone)}
                      </p>
                    ) : null}
                  </div>
                  <div className="grid gap-5 sm:grid-cols-2">
                    <div>
                      <label className="label" htmlFor="worker-password">
                        {t("onboarding.form.password")}
                      </label>
                      <input
                        id="worker-password"
                        className="field"
                        type="password"
                        value={form.password}
                        onBlur={() => markTouched("password")}
                        onChange={(e) =>
                          updateField("password", e.target.value)
                        }
                        minLength={8}
                        required
                      />
                      {passwordStrength ? (
                        <p className={`mt-2 text-sm ${passwordStrength.tone}`}>
                          {t(passwordStrength.label)}
                        </p>
                      ) : null}
                      {touched.password && validationErrors.password ? (
                        <p className="mt-2 text-sm text-rose-700">
                          {t(validationErrors.password)}
                        </p>
                      ) : null}
                    </div>
                    <div>
                      <label
                        className="label"
                        htmlFor="worker-confirm-password"
                      >
                        {t("onboarding.form.confirm_password")}
                      </label>
                      <input
                        id="worker-confirm-password"
                        className="field"
                        type="password"
                        value={form.confirm_password}
                        onBlur={() => markTouched("confirm_password")}
                        onChange={(e) =>
                          updateField("confirm_password", e.target.value)
                        }
                        minLength={8}
                        required
                      />
                      {touched.confirm_password &&
                        validationErrors.confirm_password ? (
                        <p className="mt-2 text-sm text-rose-700">
                          {t(validationErrors.confirm_password)}
                        </p>
                      ) : null}
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <p className="eyebrow">{t("onboarding.form.area")}</p>
                <div className="mt-4 grid gap-5 sm:grid-cols-2">
                  <div>
                    <label className="label" htmlFor="worker-city">
                      {t("onboarding.form.city")}
                    </label>
                    <select
                      id="worker-city"
                      className="field"
                      value={form.city}
                      onChange={(e) => updateField("city", e.target.value)}
                      disabled={locationsLoading}
                    >
                      {cityOptions.map((option) => (
                        <option key={option.id} value={option.slug}>
                          {option.display_name}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="label" htmlFor="worker-zone">
                      {t("onboarding.form.zone")}
                    </label>
                    <select
                      id="worker-zone"
                      className="field"
                      value={form.zone}
                      onBlur={() => markTouched("zone")}
                      onChange={(e) => updateField("zone", e.target.value)}
                      disabled={locationsLoading || !zoneOptions.length}
                    >
                      {zoneOptions.map((zone) => (
                        <option key={zone.id} value={zone.slug}>
                          {zone.display_name}
                        </option>
                      ))}
                    </select>
                    {touched.zone && validationErrors.zone ? (
                      <p className="mt-2 text-sm text-rose-700">
                        {t(validationErrors.zone)}
                      </p>
                    ) : null}
                  </div>
                </div>
              </div>

              <div>
                <p className="eyebrow">{t("onboarding.form.earning")}</p>
                <div className="mt-4 grid gap-5 sm:grid-cols-2">
                  <div>
                    <label className="label" htmlFor="worker-platform">
                      {t("onboarding.form.platform")}
                    </label>
                    <select
                      id="worker-platform"
                      className="field"
                      value={form.platform}
                      onChange={(e) => updateField("platform", e.target.value)}
                    >
                      {PLATFORM_OPTIONS.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="label" htmlFor="worker-hours">
                      {t("onboarding.form.hours")}
                    </label>
                    <input
                      id="worker-hours"
                      className="field"
                      type="number"
                      step="0.5"
                      value={form.working_hours}
                      onChange={(e) =>
                        updateField("working_hours", e.target.value)
                      }
                    />
                  </div>
                  <div className="sm:col-span-2">
                    <label className="label" htmlFor="worker-income">
                      {t("onboarding.form.income")}
                    </label>
                    <input
                      id="worker-income"
                      className="field"
                      type="number"
                      value={form.self_reported_income}
                      onChange={(e) =>
                        updateField("self_reported_income", e.target.value)
                      }
                    />
                  </div>
                </div>
              </div>

              <label className="flex items-start gap-3 rounded-2xl bg-surface-container-high p-4 text-sm text-on-surface-variant">
                <input
                  className="mt-1"
                  type="checkbox"
                  checked={form.consent_given}
                  onBlur={() => markTouched("consent_given")}
                  onChange={(e) =>
                    updateField("consent_given", e.target.checked)
                  }
                />
                <span>
                  {t("onboarding.form.consent")}
                </span>
              </label>
              {touched.consent_given && validationErrors.consent_given ? (
                <p className="text-sm text-rose-700">
                  {t(validationErrors.consent_given)}
                </p>
              ) : null}

              <button
                type="submit"
                className="button-primary"
                disabled={
                  loading ||
                  locationsLoading ||
                  !form.consent_given ||
                  !form.zone
                }
              >
                {loading ? t("onboarding.form.registering") : t("onboarding.form.register")}
              </button>
            </div>
          </form>

          <RiskGauge
            score={registration?.risk_score}
            breakdown={registration?.risk_breakdown}
          />
        </div>
      ) : null}

      {step === "plan" && registration ? (
        <div className="space-y-6">
          <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
            <RiskGauge
              score={registration.risk_score}
              breakdown={registration.risk_breakdown}
            />

            <div className="panel p-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="eyebrow">{t("onboarding.plans.compare.eyebrow")}</p>
                  <h3 className="mt-2 text-2xl font-bold text-primary">
                    {t("onboarding.plans.compare.title")}
                  </h3>
                  <p className="mt-3 max-w-2xl text-sm leading-6 text-on-surface-variant">
                    {t("onboarding.plans.compare.desc")}
                  </p>
                </div>
                <span className="pill bg-surface-container-high text-on-surface-variant">
                  {t("onboarding.plans.compare.options_count", { count: featuredPlans.length })}
                </span>
              </div>

              {planCatalogError ? (
                <div className="mt-5">
                  <ErrorState
                    message={planCatalogError}
                    onRetry={() =>
                      setPlanCatalogReloadKey((current) => current + 1)
                    }
                  />
                </div>
              ) : null}

              {planCatalogLoading ? (
                <div className="mt-5 rounded-2xl bg-surface-container-high p-4 text-sm text-on-surface-variant">
                  {t("onboarding.plans.refreshing")}
                </div>
              ) : null}

              {featuredPlans.length ? (
                <div className="mt-5 grid gap-3 sm:grid-cols-3">
                  {featuredPlans.map((plan) => {
                    const planName =
                      plan.display_name || humanizeSlug(plan.plan_name);

                    return (
                      <div
                        key={plan.plan_name}
                        className={clsx(
                          "rounded-2xl border p-4 transition",
                          selectedPlan === plan.plan_name
                            ? "border-ink bg-white"
                            : "border-white/10 bg-surface-container-high",
                        )}
                      >
                        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-on-surface-variant">
                          {planName}
                        </p>
                        <p className="mt-3 text-2xl font-bold">
                          {formatCurrency(plan.weekly_premium)}
                        </p>
                        <p className="mt-1 text-sm text-on-surface-variant">
                          {t("onboarding.plans.up_to", { amount: formatCurrency(plan.coverage_cap) })}
                        </p>
                        <p className="mt-3 text-sm leading-6 text-on-surface-variant">
                          {t(`onboarding.stories.${plan.plan_name}.compareFit`) || plan.description}
                        </p>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="mt-5 rounded-2xl bg-surface-container-high p-4 text-sm text-on-surface-variant">
                  {t("onboarding.plans.waiting")}
                </div>
              )}
            </div>
          </div>

          <div className="grid gap-4 xl:grid-cols-3">
            {featuredPlans.map((plan) => (
              <PlanCard
                key={plan.plan_name}
                plan={plan}
                selected={selectedPlan === plan.plan_name}
                onSelect={setSelectedPlan}
                story={{
                  eyebrow: t(`onboarding.stories.${plan.plan_name}.eyebrow`),
                  bestFor: t(`onboarding.stories.${plan.plan_name}.bestFor`),
                  compareFit: t(`onboarding.stories.${plan.plan_name}.compareFit`),
                }}
                recommendationReason={
                  plan.is_recommended
                    ? t("onboarding.recommendation_reason")
                    : ""
                }
              />
            ))}
          </div>

          {additionalPlans.length ? (
            <div className="context-panel p-6">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="eyebrow">{t("onboarding.plans.more.eyebrow")}</p>
                  <h3 className="mt-2 text-2xl font-bold text-primary">
                    {t("onboarding.plans.more.title")}
                  </h3>
                  <p className="mt-3 max-w-2xl text-sm leading-6 text-on-surface-variant">
                    {t("onboarding.plans.more.desc")}
                  </p>
                </div>
                <button
                  type="button"
                  className="button-secondary"
                  onClick={() => setShowAllPlans((current) => !current)}
                >
                  {showAllPlans
                    ? t("onboarding.plans.more.hide_more", { suffix: additionalPlans.length === 1 ? "" : "s" })
                    : t("onboarding.plans.more.show_more", { count: additionalPlans.length, suffix: additionalPlans.length === 1 ? "" : "s" })}
                </button>
              </div>

              {showAllPlans ? (
                <div className="mt-5 grid gap-4 xl:grid-cols-3">
                  {additionalPlans.map((plan) => (
                    <PlanCard
                      key={plan.plan_name}
                      plan={plan}
                      selected={selectedPlan === plan.plan_name}
                      onSelect={setSelectedPlan}
                      story={{
                        eyebrow: t(`onboarding.stories.${plan.plan_name}.eyebrow`),
                        bestFor: t(`onboarding.stories.${plan.plan_name}.bestFor`),
                        compareFit: t(`onboarding.stories.${plan.plan_name}.compareFit`),
                      }}
                      recommendationReason={
                        plan.is_recommended
                          ? t("onboarding.recommendation_reason")
                          : ""
                      }
                    />
                  ))}
                </div>
              ) : (
                <div className="mt-5 rounded-2xl bg-surface-container-high p-4 text-sm leading-6 text-on-surface-variant">
                  {t("onboarding.plans.more.footer")}
                </div>
              )}
            </div>
          ) : null}

          <div className="grid gap-6 lg:grid-cols-[1.05fr_0.95fr]">
            <div className="panel p-6">
              <p className="eyebrow">{t("onboarding.trust.eyebrow")}</p>
              <h3 className="mt-2 text-2xl font-bold text-primary">
                {t("onboarding.trust.title")}
              </h3>
              <div className="mt-4 grid gap-3 sm:grid-cols-3">
                <div className="rounded-2xl bg-surface-container-high p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-on-surface-variant">
                    {t("onboarding.trust.monitoring")}
                  </p>
                  <p className="mt-2 text-lg font-semibold">
                    {t("onboarding.trust.monitoring_cities", { count: monitoredCities })}
                  </p>
                  <p className="mt-2 text-sm leading-6 text-on-surface-variant">
                    {t("onboarding.trust.monitoring_desc")}
                  </p>
                </div>
                <div className="rounded-2xl bg-surface-container-high p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-on-surface-variant">
                    {t("onboarding.trust.decision")}
                  </p>
                  <p className="mt-2 text-lg font-semibold">
                    {t("onboarding.trust.auto_checks")}
                  </p>
                  <p className="mt-2 text-sm leading-6 text-on-surface-variant">
                    {t("onboarding.trust.decision_desc")}
                  </p>
                </div>
                <div className="rounded-2xl bg-surface-container-high p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-on-surface-variant">
                    {t("onboarding.trust.activation")}
                  </p>
                  <p className="mt-2 text-lg font-semibold">
                    {t("onboarding.trust.background")}
                  </p>
                  <p className="mt-2 text-sm leading-6 text-on-surface-variant">
                    {t("onboarding.trust.activation_desc")}
                  </p>
                </div>
              </div>
            </div>

            <div className="panel p-6">
              <p className="eyebrow">{t("onboarding.next.eyebrow")}</p>
              <h3 className="mt-2 text-2xl font-bold text-primary">
                {t("onboarding.next.title")}
              </h3>
              <div className="mt-4 space-y-3">
                <div className="rounded-2xl bg-surface-container-high p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-on-surface-variant">
                    {t("onboarding.next.step_1")}
                  </p>
                  <p className="mt-2 text-lg font-semibold">{t("onboarding.next.step_1_title")}</p>
                  <p className="mt-2 text-sm leading-6 text-on-surface-variant">
                    {t("onboarding.next.step_1_desc")}
                  </p>
                </div>
                <div className="rounded-2xl bg-surface-container-high p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-on-surface-variant">
                    {t("onboarding.next.step_2")}
                  </p>
                  <p className="mt-2 text-lg font-semibold">{t("onboarding.next.step_2_title")}</p>
                  <p className="mt-2 text-sm leading-6 text-on-surface-variant">
                    {t("onboarding.next.step_2_desc")}
                  </p>
                </div>
                <div className="rounded-2xl bg-surface-container-high p-4">
                  <p className="text-xs font-semibold uppercase tracking-[0.2em] text-on-surface-variant">
                    {t("onboarding.next.step_3")}
                  </p>
                  <p className="mt-2 text-lg font-semibold">{t("onboarding.next.step_3_title")}</p>
                  <p className="mt-2 text-sm leading-6 text-on-surface-variant">
                    {t("onboarding.next.step_3_desc")}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      ) : null}

      {step === "plan" && registration ? (
        <div className="fixed inset-x-4 bottom-4 z-30 mx-auto max-w-5xl">
          <div className="panel border-primary/20 bg-surface-container-low p-4 shadow-2xl backdrop-blur-md">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
              <div className="flex items-center gap-3">
                <p className="text-lg font-bold text-primary">
                  {t("onboarding.footer.selected")}{" "}
                  {selectedPlanData
                    ? selectedPlanData.display_name ||
                    humanizeSlug(selectedPlanData.plan_name)
                    : t("onboarding.footer.none")}
                </p>
                {selectedPlanData ? (
                  <span className="text-lg font-semibold text-primary">
                    • {formatCurrency(selectedPlanData.weekly_premium)}/week
                  </span>
                ) : null}
              </div>

              <button
                type="button"
                className="button-primary min-w-[240px] px-8 py-4 text-base"
                disabled={loading || !selectedPlanData}
                onClick={handlePurchase}
              >
                {loading ? t("onboarding.footer.activating") : t("onboarding.footer.activate")}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
