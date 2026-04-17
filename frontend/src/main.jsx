import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { Toaster } from "react-hot-toast";

import App from "./App";
import "./i18n/config";
import "./index.css";
import { ThemeProvider } from "./theme/ThemeContext";

window.addEventListener("error", (event) => {
  console.error("[RideShield Global Error]", event.error);
});

window.addEventListener("unhandledrejection", (event) => {
  console.error("[RideShield Unhandled Promise Rejection]", event.reason);
});

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <ThemeProvider>
        <App />
        <Toaster
          position="top-right"
          toastOptions={{
            duration: 3500,
            style: {
              borderRadius: "16px",
              border: "1px solid rgba(18,22,33,0.08)",
              boxShadow: "0 18px 50px rgba(18,22,33,0.08)",
            },
          }}
        />
      </ThemeProvider>
    </BrowserRouter>
  </React.StrictMode>,
);
