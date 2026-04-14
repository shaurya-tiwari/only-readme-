/**
 * i18n — lightweight translation for critical worker-facing strings.
 * Only covers worker dashboard. Admin panels stay English.
 */

const translations = {
  en: {
    // Dashboard
    "dashboard.title": "Worker Dashboard",
    "dashboard.subtitle": "Coverage, incidents, and payouts",
    "dashboard.protection_active": "Automatic protection active",
    "dashboard.no_claims": "No claim incidents yet",

    // Claim
    "claim.approved": "Claim approved",
    "claim.rejected": "Claim could not be approved",
    "claim.under_review": "Claim under review",
    "claim.payout_label": "Payout amount",
    "claim.income_loss": "Estimated income lost",
    "claim.coverage": "We covered",
    "claim.coverage_ratio": "Coverage ratio",
    "claim.select": "Select an incident",
    "claim.pick": "Pick a claim incident from the list to view detailed information.",

    // Policy
    "policy.active": "Active policy",
    "policy.expired": "Policy expired",
    "policy.renew": "Renew your coverage",
    "policy.no_policy": "No active policy",

    // Payout
    "payout.credited": "Payout credited",
    "payout.processing": "Processing payout…",
    "payout.paid": "Paid",

    // Notifications
    "notif.title": "Notifications",
    "notif.mark_read": "Mark all read",
    "notif.empty": "No notifications yet",

    // General
    "lang.toggle": "हिंदी",
  },
  hi: {
    // Dashboard
    "dashboard.title": "कर्मचारी डैशबोर्ड",
    "dashboard.subtitle": "कवरेज, घटनाएँ, और भुगतान",
    "dashboard.protection_active": "स्वचालित सुरक्षा सक्रिय",
    "dashboard.no_claims": "अभी तक कोई दावा नहीं",

    // Claim
    "claim.approved": "दावा स्वीकृत",
    "claim.rejected": "दावा स्वीकृत नहीं हो सका",
    "claim.under_review": "दावा समीक्षा में",
    "claim.payout_label": "भुगतान राशि",
    "claim.income_loss": "अनुमानित आय हानि",
    "claim.coverage": "हमने कवर किया",
    "claim.coverage_ratio": "कवरेज अनुपात",
    "claim.select": "एक घटना चुनें",
    "claim.pick": "विस्तृत जानकारी देखने के लिए सूची से दावा चुनें।",

    // Policy
    "policy.active": "सक्रिय पॉलिसी",
    "policy.expired": "पॉलिसी समाप्त",
    "policy.renew": "अपनी सुरक्षा नवीनीकृत करें",
    "policy.no_policy": "कोई सक्रिय पॉलिसी नहीं",

    // Payout
    "payout.credited": "भुगतान जमा",
    "payout.processing": "भुगतान प्रक्रिया में…",
    "payout.paid": "भुगतान हो गया",

    // Notifications
    "notif.title": "सूचनाएँ",
    "notif.mark_read": "सब पढ़ा हुआ",
    "notif.empty": "अभी कोई सूचना नहीं",

    // General
    "lang.toggle": "EN",
  },
};

let currentLang = localStorage.getItem("rs_lang") || "en";

export function t(key) {
  return translations[currentLang]?.[key] || translations.en[key] || key;
}

export function getLang() {
  return currentLang;
}

export function setLang(lang) {
  currentLang = lang;
  localStorage.setItem("rs_lang", lang);
}

export function toggleLang() {
  const next = currentLang === "en" ? "hi" : "en";
  setLang(next);
  return next;
}
