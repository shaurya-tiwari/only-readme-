import client from "./client";

export const triggersApi = {
  status: (params) => client.get("/api/triggers/status", { params }),
  check: (payload) => client.post("/api/triggers/check", payload),
  scenario: (scenarioName) => client.post(`/api/triggers/scenario/${scenarioName}`),
  reset: () => client.post("/api/triggers/reset"),
};
