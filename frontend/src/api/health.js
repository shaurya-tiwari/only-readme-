import client from "./client";

export const healthApi = {
  getApp: () => client.get("/health", { skipToast: true }),
  getDb: () => client.get("/health/db", { skipToast: true }),
  getConfig: () => client.get("/health/config", { skipToast: true }),
};
