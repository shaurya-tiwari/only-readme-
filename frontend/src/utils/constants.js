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
    title: "Automatic rain payout",
    summary: "Stable worker in South Delhi with a covered rain disruption and a clean payout path.",
    outcome: "Expected to auto-create the claim and release payout automatically.",
    zone: "south_delhi",
    city: "delhi",
    setup: "Fixed worker profile: trusted account, repeated delivery history, smart protect plan.",
    accent: "from-storm to-sky-200",
  },
  {
    id: "borderline_review",
    title: "Borderline manual review",
    summary: "Edge worker in East Delhi with a real platform drop but not enough clean history for instant payout.",
    outcome: "Expected to hold the claim for review instead of guessing on payout.",
    zone: "east_delhi",
    city: "delhi",
    setup: "Fixed worker profile: light history, weaker trust profile, assured plan.",
    accent: "from-gold to-amber-100",
  },
  {
    id: "suspicious_activity",
    title: "Suspicious activity check",
    summary: "South Delhi rain disruption with a new account pattern that does not look safe enough for instant payout.",
    outcome: "Expected to block the payout lane with delay or rejection.",
    zone: "south_delhi",
    city: "delhi",
    setup: "Fixed worker profile: weak account history, low trust, and no stable device pattern.",
    accent: "from-ember to-rose-100",
  },
  {
    id: "gps_spoofing_attack",
    title: "GPS spoofing detection",
    summary: "Real disruption signal but GPS data reveals teleportation-class movement anomalies — impossible velocity between pings.",
    outcome: "Expected to flag and route to review due to movement fraud signals.",
    zone: "south_delhi",
    city: "delhi",
    setup: "Fixed worker profile: moderate trust, but GPS pings show Delhi↔Mumbai teleportation within minutes.",
    accent: "from-red-900 to-purple-200",
  },
];

export const STORAGE_KEYS = {
  onboardingDraft: "rideshield.onboardingDraft",
  scenarioLabPresets: "rideshield.scenarioLabPresets",
};
