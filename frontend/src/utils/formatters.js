import clsx from "clsx";
import { format, formatDistanceToNow } from "date-fns";

export function formatCurrency(value) {
  if (value === null || value === undefined) {
    return "INR 0";
  }
  return `INR ${Math.round(Number(value)).toLocaleString("en-IN")}`;
}

export function formatPercent(value, digits = 1) {
  if (value === null || value === undefined) {
    return "0%";
  }
  return `${Number(value).toFixed(digits)}%`;
}

export function formatScore(value) {
  if (value === null || value === undefined) {
    return "--";
  }
  return Number(value).toFixed(3);
}

export function formatRelative(value) {
  if (!value) {
    return "--";
  }
  return formatDistanceToNow(new Date(value), { addSuffix: true });
}

export function formatDateTime(value) {
  if (!value) {
    return "--";
  }
  return format(new Date(value), "dd MMM yyyy, h:mm a");
}

export function humanizeSlug(value = "") {
  return value
    .split("_")
    .filter(Boolean)
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(" ");
}

export function statusPill(status) {
  const styles = {
    approved: "bg-emerald-100 text-emerald-800",
    delayed: "bg-amber-100 text-amber-800",
    rejected: "bg-rose-100 text-rose-800",
    active: "bg-sky-100 text-sky-800",
    pending: "bg-slate-100 text-slate-800",
    completed: "bg-emerald-100 text-emerald-800",
  };

  return clsx("pill", styles[status] || "bg-slate-100 text-slate-800");
}

export function riskLabel(score) {
  const numeric = Number(score || 0);
  if (numeric < 0.25) {
    return { label: "Stable", tone: "text-emerald-700" };
  }
  if (numeric < 0.5) {
    return { label: "Guarded", tone: "text-gold" };
  }
  if (numeric < 0.75) {
    return { label: "Elevated", tone: "text-orange-700" };
  }
  return { label: "Critical", tone: "text-rose-700" };
}
