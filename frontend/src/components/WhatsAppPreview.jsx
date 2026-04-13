/**
 * Simulated WhatsApp notification preview.
 * Presentation-only — shows what real mobile delivery would look like.
 */

export default function WhatsAppPreview({ claim }) {
  if (!claim || claim.status !== "approved") return null;

  const payout = claim.final_payout || claim.income_loss?.payout_amount || 0;
  const loss = claim.income_loss?.estimated_income_loss || 0;
  const trigger = (claim.trigger_type || "disruption").replace(/_/g, " ");

  return (
    <div
      style={{
        marginTop: "16px",
        borderRadius: "16px",
        background: "linear-gradient(135deg, #075e54 0%, #128c7e 100%)",
        padding: "16px",
        maxWidth: "340px",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "12px" }}>
        <span style={{ fontSize: "20px" }}>📲</span>
        <span style={{ fontSize: "11px", fontWeight: 700, color: "#25d366", letterSpacing: "0.1em", textTransform: "uppercase" }}>
          WhatsApp Alert Preview
        </span>
      </div>
      <div
        style={{
          background: "#dcf8c6",
          borderRadius: "12px",
          padding: "12px 14px",
          color: "#111",
          fontSize: "13px",
          lineHeight: 1.6,
        }}
      >
        <p style={{ fontWeight: 600 }}>🛡️ RideShield</p>
        <p style={{ marginTop: "4px" }}>
          {trigger.charAt(0).toUpperCase() + trigger.slice(1)} disruption detected.
        </p>
        <p>Estimated loss: ₹{Math.round(loss)}</p>
        <p>Coverage: ₹{Math.round(payout)}</p>
        <p style={{ marginTop: "4px", fontWeight: 600, color: "#128c7e" }}>
          ✅ Claim processed automatically.
        </p>
        <p style={{ marginTop: "8px", fontSize: "10px", color: "#666", textAlign: "right" }}>
          {new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" })}
        </p>
      </div>
      <p style={{ marginTop: "8px", fontSize: "10px", color: "rgba(255,255,255,0.5)", textAlign: "center" }}>
        Production: integrated with WhatsApp Business API
      </p>
    </div>
  );
}
