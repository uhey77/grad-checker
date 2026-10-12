import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import { createApplication } from "./app/composition/createApplication";
import "./style.css";

const application = createApplication();
const verificationToken =
  new URLSearchParams(window.location.hash.slice(1)).get(
    "verification_token",
  ) || "";
if (verificationToken)
  window.history.replaceState(
    null,
    "",
    window.location.pathname + window.location.search,
  );
createRoot(document.getElementById("app")!).render(
  <StrictMode>
    <App application={application} verificationToken={verificationToken} />
  </StrictMode>,
);
