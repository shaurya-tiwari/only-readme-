import client from "./client";

export const analyticsApi = {
  adminOverview: (params) => client.get("/api/analytics/admin-overview", { params }),
  adminForecast: () => client.get("/api/analytics/admin-forecast"),
  forecast: (params) => client.get("/api/analytics/forecast", { params }),
  zoneRisk: (params) => client.get("/api/analytics/zone-risk", { params }),
  models: () => client.get("/api/analytics/models"),
};
