export const CITY_OPTIONS = [
  { value: "delhi", label: "Delhi" },
  { value: "mumbai", label: "Mumbai" },
  { value: "bengaluru", label: "Bengaluru" },
  { value: "chennai", label: "Chennai" },
];

export const CITY_ZONES = {
  delhi: [
    "south_delhi",
    "north_delhi",
    "east_delhi",
    "west_delhi",
    "central_delhi",
  ],
  mumbai: ["south_mumbai", "western_suburbs", "eastern_suburbs", "navi_mumbai"],
  bengaluru: ["koramangala", "whitefield", "indiranagar", "jayanagar", "electronic_city"],
  chennai: ["t_nagar", "anna_nagar", "adyar", "velachery"],
};

export const PLATFORM_OPTIONS = [
  { value: "zomato", label: "Zomato" },
  { value: "swiggy", label: "Swiggy" },
  { value: "blinkit", label: "Blinkit" },
  { value: "dunzo", label: "Dunzo" },
];

export const SCENARIOS = [
  {
    id: "clean_legit",
    title: "Automatic Rain Payout",
    summary: "Stable worker, covered rain disruption, and clean payout path.",
    outcome: "Expected path: Claim is created and payout is released automatically.",
    city: "delhi",
    zone: "south_delhi",
    setup: "Rahul Kumar (legit) · Zomato Smart Protect",
    accent: "from-storm to-sky-200",
  },
  {
    id: "borderline_review",
    title: "Borderline Manual Review",
    summary: "Platform drop with weaker history and a guarded review lane.",
    outcome: "Expected path: Claim is held for review because the evidence mix is incomplete.",
    city: "delhi",
    zone: "east_delhi",
    setup: "Arun Patel (edge) · Zomato Assured Plan",
    accent: "from-gold to-amber-100",
  },
  {
    id: "suspicious_activity",
    title: "Suspicious Activity Check",
    summary: "Real disruption signal, but the account pattern looks unsafe.",
    outcome: "Expected path: Claim is blocked from instant payout because the account pattern is not trusted.",
    city: "delhi",
    zone: "south_delhi",
    setup: "Vikram Singh (fraud) · Zomato Smart Protect",
    accent: "from-ember to-rose-100",
  },
  {
    id: "gps_spoofing_attack",
    title: "GPS Spoofing Detection",
    summary: "Real disruption signal but GPS data reveals teleportation-class movement anomalies.",
    outcome: "Expected path: Claim is flagged and routed to review due to impossible GPS movement patterns.",
    city: "delhi",
    zone: "south_delhi",
    setup: "Deepak Sharma (spoof) · Zomato Smart Protect",
    accent: "from-slate-500 to-slate-100",
  },
];

export const STORAGE_KEYS = {
  onboardingDraft: "rideshield.onboardingDraft",
};
