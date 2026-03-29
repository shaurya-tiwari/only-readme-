import client from "./client";

export const analyticsApi = {
  adminOverview: (params) => client.get("/api/analytics/admin-overview", { params }),
};
