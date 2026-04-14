import client from "./client";

export const healthApi = {
  getApp: () => client.get("/health", { skipToast: true }),
  getDb: () => client.get("/health/db", { skipToast: true }),
  getRuntime: () => client.get("/config/runtime", { skipToast: true }),
  getSignals: () => client.get("/health/signals", { skipToast: true }),
  getDiagnostics: () => client.get("/health/diagnostics", { skipToast: true }),
  getConfig: () => client.get("/health/config", { skipToast: true }),
};
