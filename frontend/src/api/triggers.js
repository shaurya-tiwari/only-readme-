import client from "./client";

export const triggersApi = {
  status: (params) => client.get("/api/triggers/status", { params }),
  check: (payload) => client.post("/api/triggers/check", payload),
  scenario: (scenarioName) => client.post(`/api/triggers/scenario/${scenarioName}`),
  demoScenario: (scenarioId) => client.post(`/api/triggers/demo-scenario/${scenarioId}`),
  labRun: (payload) => client.post("/api/triggers/lab-run", payload),
  reset: () => client.post("/api/triggers/reset"),
};
