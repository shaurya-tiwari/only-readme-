import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { Toaster } from "react-hot-toast";

import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
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
    </BrowserRouter>
  </React.StrictMode>,
);
