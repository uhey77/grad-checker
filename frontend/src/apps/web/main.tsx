import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App.tsx";
import { createApplication } from "./composition/createApplication.ts";
import "./style.css";

const application = createApplication();
createRoot(document.getElementById("app")!).render(
  <StrictMode>
    <App application={application} />
  </StrictMode>,
);
