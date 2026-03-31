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
    id: "heavy_rain",
    title: "Heavy Rain",
    summary: "Legitimate weather disruption for covered workers.",
    outcome: "Expected to auto-approve legitimate claims and execute payouts.",
    accent: "from-storm to-sky-200",
  },
  {
    id: "platform_outage",
    title: "Platform Outage",
    summary: "Edge-case income loss with weaker behavioral history.",
    outcome: "Expected to route some claims to manual review.",
    accent: "from-gold to-amber-100",
  },
  {
    id: "compound_disaster",
    title: "Compound Disaster",
    summary: "Rain, AQI, traffic, and outage stacked together.",
    outcome: "Expected to stress the engine across multiple triggers.",
    accent: "from-ember to-rose-100",
  },
  {
    id: "hazardous_aqi",
    title: "Hazardous AQI",
    summary: "Pollution spike that tests parametric health coverage.",
    outcome: "Expected to create eligible AQI-linked claims.",
    accent: "from-slate-500 to-slate-100",
  },
];

export const STORAGE_KEYS = {
  workerId: "rideshield.workerId",
};
