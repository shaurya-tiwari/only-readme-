import client from "./client";

export const workersApi = {
  register: (payload) => client.post("/api/workers/register", payload),
  list: (params) => client.get("/api/workers/", { params }),
  profile: (workerId) => client.get(`/api/workers/me/${workerId}`),
  update: (workerId, payload) => client.put(`/api/workers/me/${workerId}`, payload),
  risk: (workerId) => client.get(`/api/workers/risk-score/${workerId}`),
};
