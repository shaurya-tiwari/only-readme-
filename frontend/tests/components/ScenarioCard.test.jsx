import { fireEvent, render, screen } from "@testing-library/react";

import ScenarioCard from "../../src/components/ScenarioCard";

describe("ScenarioCard", () => {
  const scenario = {
    id: "heavy_rain",
    title: "Heavy Rain",
    summary: "Legitimate weather disruption for covered workers.",
    outcome: "Expected to auto-approve legitimate claims and execute payouts.",
    city: "delhi",
    zone: "south_delhi",
    setup: "Fixed worker profile for demo validation.",
  };

  it("renders scenario results with strong contrast surfaces instead of pale inset panels", () => {
    render(
      <ScenarioCard
        scenario={scenario}
        running={false}
        thresholds={{ rain: 25, traffic: 0.75, platform_outage: 0.6, aqi: 300, heat: 44 }}
        onRun={() => {}}
        result={{
          events_created: 5,
          events_extended: 0,
          claims_generated: 7,
          claims_approved: 3,
          claims_delayed: 2,
          claims_rejected: 2,
          total_payout: 204,
          details: [
            {
              signals: {
                rain: 31,
                traffic: 0.63,
                platform_outage: 0.72,
                aqi: 180,
                heat: 35,
              },
              triggers_fired: ["rain", "platform_outage"],
            },
          ],
        }}
      />,
    );

    const causePanel = screen.getByText(/Cause and effect/i).closest("div");
    const incidentsValue = screen.getByText("5");
    const payoutValue = screen.getByText("INR 204");
    const incidentsLabel = screen.getByText("Incidents");

    expect(causePanel.className).toContain("bg-surface-container-high/90");
    expect(causePanel.className).not.toContain("bg-white/90");
    expect(incidentsValue.className).toContain("text-2xl");
    expect(payoutValue.className).toContain("sm:text-3xl");
    expect(incidentsLabel.parentElement.className).toContain("justify-between");
    expect(screen.getByText(/Triggers crossed: Rain, Platform Outage/i)).toBeInTheDocument();
  });

  it("triggers the run callback from the primary action", () => {
    const onRun = vi.fn();

    render(<ScenarioCard scenario={scenario} running={false} result={null} thresholds={{}} onRun={onRun} />);

    fireEvent.click(screen.getByRole("button", { name: /run/i }));
    expect(onRun).toHaveBeenCalledWith("heavy_rain");
  });
});
