import client from "./client";

export const notificationsApi = {
  list: (workerId, params) => client.get(`/api/notifications/worker/${workerId}`, { params }),
  markRead: (workerId, notificationIds) =>
    client.post(`/api/notifications/worker/${workerId}/mark-read`, {
      notification_ids: notificationIds || null,
    }),
};
