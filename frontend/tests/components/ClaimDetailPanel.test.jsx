import { render, screen } from "@testing-library/react";

import ClaimDetailPanel from "../../src/components/ClaimDetailPanel";

describe("ClaimDetailPanel", () => {
  it("shows the empty-state copy when no claim is selected", () => {
    render(<ClaimDetailPanel claim={null} />);

    expect(screen.getByText(/Select an incident/i)).toBeInTheDocument();
    expect(screen.getByText(/Pick a claim incident/i)).toBeInTheDocument();
  });

  it("renders claim check intensity and payout breakdown when a claim is present", () => {
    render(
      <ClaimDetailPanel
        claim={{
          status: "delayed",
          created_at: "2026-04-02T01:30:00Z",
          final_payout: 170,
          disruption_hours: 2,
          peak_multiplier: 1.3,
          final_score: 0.81,
          fraud_score: 0.42,
          event_confidence: 0.77,
          trust_score: 0.68,
          decision_breakdown: {
            explanation: "Manual review stayed open because fraud signals were elevated.",
            inputs: {
              incident_triggers: ["platform_outage", "rain"],
              covered_triggers: ["platform_outage"],
            },
            breakdown: {
              disruption_component: 0.22,
              confidence_component: 0.18,
              fraud_component: 0.31,
              trust_component: 0.1,
              flag_penalty: 0.04,
            },
            fraud_model: {
              fraud_probability: 0.44,
              model_version: "fraud-model-v1",
              fallback_used: false,
              top_factors: [
                { factor: "claim_frequency", label: "Claim frequency" },
                { factor: "income_spike", label: "Income spike" },
              ],
            },
          },
          payout_breakdown: {
            income_per_hour: 100,
            net_income_per_hour: 85,
            operating_cost_factor: 0.85,
          },
        }}
      />,
    );

    expect(screen.getByText(/44% check intensity/i)).toBeInTheDocument();
    expect(screen.getByText(/fraud-model-v1 - hybrid scoring active/i)).toBeInTheDocument();
    expect(screen.getByText("Claim frequency")).toBeInTheDocument();
    expect(screen.getByText(/Gross hourly reference/i)).toBeInTheDocument();
    expect(screen.getByText(/Net protected hourly/i)).toBeInTheDocument();
    expect(screen.getByText(/Operating-cost factor: 85%/i)).toBeInTheDocument();
  });
});
