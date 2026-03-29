import client from "./client";

export const policiesApi = {
  plans: (workerId) => client.get(`/api/policies/plans/${workerId}`),
  create: (payload) => client.post("/api/policies/create", payload),
  active: (workerId) => client.get(`/api/policies/active/${workerId}`),
  history: (workerId) => client.get(`/api/policies/history/${workerId}`),
  activatePending: () => client.post("/api/policies/activate-pending"),
  forceActivate: (workerId) =>
    client.post("/api/policies/admin/force-activate", null, { params: workerId ? { worker_id: workerId } : undefined }),
};
