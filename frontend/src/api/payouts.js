import client from "./client";

export const payoutsApi = {
  worker: (workerId, params) => client.get(`/api/payouts/worker/${workerId}`, { params }),
  detail: (payoutId) => client.get(`/api/payouts/detail/${payoutId}`),
  stats: (params) => client.get("/api/payouts/stats", { params }),
};
