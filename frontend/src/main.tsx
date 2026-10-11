import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { SubjectListPage } from "./presentation/subject-list/SubjectListPage";
import "./style.css";
import { createSubjectListUseCases } from "./application/subject-list/SubjectListUseCases";
import { HttpSubjectListRepository } from "./infrastructure/subject-list/HttpSubjectListRepository";

const subjectListUseCases = createSubjectListUseCases(
  new HttpSubjectListRepository("/api/dev/subject-list"),
);

createRoot(document.getElementById("app")!).render(
  <StrictMode>
    <SubjectListPage useCases={subjectListUseCases} />
  </StrictMode>,
);
