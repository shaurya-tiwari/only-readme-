import client from "./client";

export const eventsApi = {
  active: (params) => client.get("/api/events/active", { params }),
  history: (params) => client.get("/api/events/history", { params }),
  detail: (eventId) => client.get(`/api/events/detail/${eventId}`),
  byZone: (zoneName, params) => client.get(`/api/events/zone/${zoneName}`, { params }),
};
