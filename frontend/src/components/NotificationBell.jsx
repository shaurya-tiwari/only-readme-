import { useEffect, useState, useRef } from "react";
import { Bell } from "lucide-react";
import { notificationsApi } from "../api/notifications";
import { useAuth } from "../auth/AuthContext";
import { t } from "../utils/i18n";

const CATEGORY_ICONS = {
  claim_approved: "✅",
  claim_review: "⏳",
  claim_rejected: "❌",
  payout_credited: "💰",
  disruption_alert: "⚡",
  policy_expiring: "⏰",
};

function timeAgo(dateStr) {
  if (!dateStr) return "";
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

export default function NotificationBell() {
  const { session, role } = useAuth();
  const [open, setOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const ref = useRef(null);

  const workerId = session?.session?.worker_id;

  // Close on outside click
  useEffect(() => {
    function handleClick(e) {
      if (ref.current && !ref.current.contains(e.target)) setOpen(false);
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  // Fetch on open
  useEffect(() => {
    if (!open || !workerId || role === "admin") return;
    setLoading(true);
    notificationsApi
      .list(workerId, { limit: 20 })
      .then((res) => {
        setNotifications(res.data?.notifications || []);
        setUnreadCount(res.data?.unread_count || 0);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [open, workerId, role]);

  // Poll unread count every 30s
  useEffect(() => {
    if (!workerId || role === "admin") return;
    const poll = () => {
      notificationsApi
        .list(workerId, { unread_only: true, limit: 1 })
        .then((res) => setUnreadCount(res.data?.unread_count || 0))
        .catch(() => {});
    };
    poll();
    const interval = setInterval(poll, 30000);
    return () => clearInterval(interval);
  }, [workerId, role]);

  async function handleMarkAllRead() {
    if (!workerId) return;
    await notificationsApi.markRead(workerId);
    setUnreadCount(0);
    setNotifications((prev) => prev.map((n) => ({ ...n, is_read: true })));
  }

  // Admin doesn't have notifications yet — keep the toast fallback
  if (role === "admin") {
    return (
      <button
        type="button"
        onClick={() => {
          import("react-hot-toast").then((m) =>
            m.default("No new alerts", { icon: "🔔" })
          );
        }}
        aria-label="Notifications"
        className="rounded-full bg-surface-container-high p-3 text-on-surface-variant transition hover:bg-surface-container-highest"
      >
        <Bell size={16} />
      </button>
    );
  }

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label="Notifications"
        className="rounded-full bg-surface-container-high p-3 text-on-surface-variant transition hover:bg-surface-container-highest"
        style={{ position: "relative" }}
      >
        <Bell size={16} />
        {unreadCount > 0 && (
          <span
            style={{
              position: "absolute",
              top: "4px",
              right: "4px",
              width: "18px",
              height: "18px",
              borderRadius: "50%",
              background: "#ef5350",
              color: "white",
              fontSize: "10px",
              fontWeight: 700,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              lineHeight: 1,
            }}
          >
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div
          style={{
            position: "absolute",
            right: 0,
            top: "calc(100% + 8px)",
            width: "360px",
            maxHeight: "420px",
            overflowY: "auto",
            borderRadius: "20px",
            border: "1px solid rgba(69, 70, 79, 0.2)",
            background: "var(--surface-container, #1c1c24)",
            boxShadow: "0 12px 48px rgba(0,0,0,0.5)",
            zIndex: 100,
          }}
        >
          <div
            style={{
              padding: "16px",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              borderBottom: "1px solid rgba(69, 70, 79, 0.15)",
            }}
          >
            <span style={{ fontWeight: 700, fontSize: "14px", color: "var(--primary)" }}>
              {t("notif.title")}
            </span>
            {unreadCount > 0 && (
              <button
                type="button"
                onClick={handleMarkAllRead}
                style={{
                  fontSize: "12px",
                  color: "var(--on-surface-variant)",
                  background: "none",
                  border: "none",
                  cursor: "pointer",
                  textDecoration: "underline",
                }}
              >
                {t("notif.mark_read")}
              </button>
            )}
          </div>

          {loading && (
            <div style={{ padding: "24px", textAlign: "center", color: "var(--on-surface-variant)", fontSize: "13px" }}>
              Loading…
            </div>
          )}

          {!loading && notifications.length === 0 && (
            <div style={{ padding: "24px", textAlign: "center", color: "var(--on-surface-variant)", fontSize: "13px" }}>
              {t("notif.empty")}
            </div>
          )}

          {!loading &&
            notifications.map((n) => (
              <div
                key={n.id}
                style={{
                  padding: "12px 16px",
                  borderBottom: "1px solid rgba(69, 70, 79, 0.1)",
                  background: n.is_read ? "transparent" : "rgba(108, 99, 255, 0.06)",
                  transition: "background 0.2s",
                }}
              >
                <div style={{ display: "flex", gap: "10px", alignItems: "flex-start" }}>
                  <span style={{ fontSize: "18px", lineHeight: 1.2 }}>
                    {CATEGORY_ICONS[n.category] || "📢"}
                  </span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                      <p style={{ fontWeight: 600, fontSize: "13px", color: "var(--on-surface)" }}>
                        {n.title}
                      </p>
                      <span style={{ fontSize: "11px", color: "var(--on-surface-variant)", whiteSpace: "nowrap", marginLeft: "8px" }}>
                        {timeAgo(n.created_at)}
                      </span>
                    </div>
                    {n.body && (
                      <p style={{ fontSize: "12px", color: "var(--on-surface-variant)", marginTop: "4px", lineHeight: 1.5 }}>
                        {n.body}
                      </p>
                    )}
                  </div>
                </div>
              </div>
            ))}
        </div>
      )}
    </div>
  );
}
