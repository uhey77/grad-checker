import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { CourseCatalogPage } from "./presentation/course-catalog/CourseCatalogPage";
import "./style.css";
import { createCatalogUseCases } from "./application/course-catalog/CatalogUseCases";
import { HttpCatalogRepository } from "./infrastructure/course-catalog/HttpCatalogRepository";

const catalogUseCases = createCatalogUseCases(
  new HttpCatalogRepository("/api/dev/course-catalog"),
);

createRoot(document.getElementById("app")!).render(
  <StrictMode>
    <CourseCatalogPage useCases={catalogUseCases} />
  </StrictMode>,
);
