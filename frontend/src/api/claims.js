import client from "./client";

export const claimsApi = {
  worker: (workerId, params) => client.get(`/api/claims/worker/${workerId}`, { params }),
  detail: (claimId) => client.get(`/api/claims/detail/${claimId}`),
  queue: () => client.get("/api/claims/review-queue"),
  resolve: (claimId, payload) => client.post(`/api/claims/resolve/${claimId}`, payload, { timeout: 120000 }),
  stats: (params) => client.get("/api/claims/stats", { params }),
};
