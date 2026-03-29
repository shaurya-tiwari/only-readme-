import axios from "axios";
import toast from "react-hot-toast";

import { getStoredToken } from "../auth/session";

const client = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "",
  timeout: 30000,
});

client.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

client.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail = error.response?.data?.detail;
    const message = Array.isArray(detail) ? detail.map((item) => item.msg).join(", ") : detail || error.message;
    if (!error.config?.skipToast) {
      toast.error(message || "Request failed");
    }
    return Promise.reject(error);
  },
);

export default client;
