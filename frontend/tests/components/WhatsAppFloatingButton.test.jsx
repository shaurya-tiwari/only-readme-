import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import WhatsAppFloatingButton from "../../src/components/WhatsAppFloatingButton";
import { AuthProvider } from "../../src/auth/AuthContext";

// Mock AuthContext
vi.mock("../../src/auth/AuthContext", () => ({
  useAuth: () => ({
    isAuthenticated: false,
    role: null
  }),
  AuthProvider: ({ children }) => <div>{children}</div>
}));

describe("WhatsAppFloatingButton", () => {
  it("renders correctly with the expected link", () => {
    render(
      <AuthProvider>
        <WhatsAppFloatingButton />
      </AuthProvider>
    );
    
    const links = screen.getAllByRole("link");
    const waLink = links.find(l => l.getAttribute("href")?.includes("wa.me"));
    
    expect(waLink).toBeInTheDocument();
    expect(waLink).toHaveAttribute("href", "https://wa.me/15551908959?text=hi");
    expect(waLink).toHaveAttribute("target", "_blank");
  });

  it("contains the lucide message circle icon", () => {
    const { container } = render(
      <AuthProvider>
        <WhatsAppFloatingButton />
      </AuthProvider>
    );
    
    // MessageCircle usually renders as an svg
    const svg = container.querySelector("svg");
    expect(svg).toBeInTheDocument();
  });
});
