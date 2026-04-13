import clsx from "clsx";
import { format, formatDistanceToNow } from "date-fns";

export function formatCurrency(value) {
  if (value === null || value === undefined) {
    return "INR 0";
  }
  return `INR ${Math.round(Number(value)).toLocaleString("en-IN")}`;
}

export function weeklyToDaily(value) {
  const numeric = Number(value || 0);
  if (Number.isNaN(numeric) || numeric <= 0) {
    return 0;
  }
  return Math.max(1, Math.round(numeric / 7));
}

export function formatPercent(value, digits = 1) {
  if (value === null || value === undefined) {
    return "0%";
  }
  const numeric = Number(value);
  if (Number.isNaN(numeric)) {
    return "--";
  }
  return `${numeric.toFixed(digits)}%`;
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
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "--";
  }
  return formatDistanceToNow(date, { addSuffix: true });
}

export function formatDateTime(value) {
  if (!value) {
    return "--";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "--";
  }
  return format(date, "dd MMM yyyy, h:mm a");
}

export function formatHours(value) {
  if (value === null || value === undefined) {
    return "--";
  }
  const numeric = Number(value);
  if (Number.isNaN(numeric)) {
    return "--";
  }
  const absolute = Math.abs(numeric);
  if (absolute < 1) {
    return "<1h";
  }
  return `${Math.round(absolute)}h`;
}

export function formatReviewWindow(hoursUntilDeadline) {
  if (hoursUntilDeadline === null || hoursUntilDeadline === undefined) {
    return "--";
  }
  const numeric = Number(hoursUntilDeadline);
  if (Number.isNaN(numeric)) {
    return "--";
  }
  if (numeric < 0) {
    return `Overdue by ${formatHours(Math.abs(numeric))}`;
  }
  if (numeric === 0) {
    return "Due now";
  }
  return `Due in ${formatHours(numeric)}`;
}

export function humanizeSlug(value = "") {
  return String(value ?? "")
    .split("_")
    .filter(Boolean)
    .map((part) => part[0].toUpperCase() + part.slice(1))
    .join(" ");
}

export function statusPill(status) {
  // Dark-adapted status pill classes (Aegis Nocturne)
  const styles = {
    approved:  "badge-active",
    completed: "badge-active",
    active:    "badge-active",
    processing:"badge-guarded",
    delayed:   "badge-pending",
    pending:   "badge-pending",
    failed:    "badge-error",
    rejected:  "badge-error",
  };

  return clsx("pill", styles[status] || "bg-surface-container-high text-on-surface-variant");
}

export function decisionConfidenceCopy(band, claimStatus) {
  if (band === "high") {
    return "High confidence approval";
  }
  if (band === "moderate") {
    return claimStatus === "delayed" ? "Moderate confidence review" : "Moderate confidence decision";
  }
  if (band === "low") {
    return "Needs manual review";
  }
  if (claimStatus === "delayed") {
    return "Needs manual review";
  }
  return "Decision confidence pending";
}

export function riskLabel(score) {
  const numeric = Number(score || 0);
  if (numeric < 0.25) {
    return { label: "Stable",   tone: "text-primary" };
  }
  if (numeric < 0.5) {
    return { label: "Guarded",  tone: "text-on-tertiary-container" };
  }
  if (numeric < 0.75) {
    return { label: "Elevated", tone: "text-secondary" };
  }
  return { label: "Critical",   tone: "text-error" };
}
