import {
  type SubjectListUseCases,
  emptyFilters,
  filterSubjects,
  sortSubjects,
  isSubjectSortOrder,
  type SubjectSortOrder,
} from "../../modules/subjects/public.ts";
import { useCallback, useState } from "react";

import { useRemote } from "../useRemote";
import { subjectListErrorMessage } from "./errors";

export function useSubjectList(useCases: SubjectListUseCases) {
  const [attempt, setAttempt] = useState(0);
  const [chosenId, setChosenId] = useState("");
  const [filters, setFilters] = useState(emptyFilters);
  const [sortOrder, setSortOrder] = useState<SubjectSortOrder>("handbook");
  const programState = useRemote("programs", useCases.listPrograms, attempt);
  const programs = programState.status === "ready" ? programState.data : [];
  const curriculumId = chosenId || programs[0]?.curriculumId || "";
  const loadSubjectList = useCallback(
    (signal: AbortSignal) => useCases.getSubjectList(curriculumId, signal),
    [useCases, curriculumId],
  );
  const subjectListState = useRemote(
    curriculumId || null,
    loadSubjectList,
    attempt,
  );
  const subjectList =
    subjectListState.status === "ready" ? subjectListState.data : null;
  const categories = new Map(
    subjectList?.subjects.flatMap((subject) =>
      subject.classificationPath[0]
        ? [
            [
              subject.classificationPath[0].id,
              subject.classificationPath[0].name,
            ] as const,
          ]
        : [],
    ),
  );
  const faculties = [
    ...new Set(subjectList?.subjects.map((subject) => subject.facultyName)),
  ];
  const visible = sortSubjects(
    filterSubjects(subjectList?.subjects ?? [], filters),
    sortOrder,
  );
  const error =
    programState.status === "error"
      ? subjectListErrorMessage(programState.error)
      : subjectListState.status === "error"
        ? subjectListErrorMessage(subjectListState.error)
        : null;
  const noPrograms = programState.status === "ready" && programs.length === 0;
  const changeFilter = (key: keyof typeof filters, value: string) =>
    setFilters((previous) => ({ ...previous, [key]: value }));
  return {
    programs,
    curriculumId,
    subjectList,
    categories,
    faculties,
    visible,
    error,
    noPrograms,
    filters,
    sortOrder,
    changeFilter,
    chooseProgram: (id: string) => {
      setChosenId(id);
      setFilters(emptyFilters);
    },
    changeSort: (value: string) => {
      if (isSubjectSortOrder(value)) setSortOrder(value);
    },
    resetFilters: () => setFilters(emptyFilters),
    retry: () => setAttempt((x) => x + 1),
  };
}
