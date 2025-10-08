import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

import "./index.css";
import App from "./App";
import { SessionProvider } from "@/lib/session";
import { ProjectProvider } from "@/lib/project";

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Elemento root não encontrado");
}

createRoot(rootElement).render(
  <StrictMode>
    <SessionProvider>
      <ProjectProvider>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </ProjectProvider>
    </SessionProvider>
  </StrictMode>,
);
