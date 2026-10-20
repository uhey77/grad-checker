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
  const [programAttempt, setProgramAttempt] = useState(0);
  const [subjectAttempt, setSubjectAttempt] = useState(0);
  const [chosenId, setChosenId] = useState("");
  const [filters, setFilters] = useState(emptyFilters);
  const [sortOrder, setSortOrder] = useState<SubjectSortOrder>("handbook");
  const loadPrograms = useCallback(
    (signal: AbortSignal) => useCases.listPrograms.execute(signal),
    [useCases],
  );
  const programState = useRemote("programs", loadPrograms, programAttempt);
  const programs = programState.status === "ready" ? programState.data : [];
  const curriculumId =
    programs.find((program) => program.curriculumId === chosenId)
      ?.curriculumId ||
    programs[0]?.curriculumId ||
    "";
  const loadSubjectList = useCallback(
    (signal: AbortSignal) =>
      useCases.getSubjectList.execute(curriculumId, signal),
    [useCases, curriculumId],
  );
  const subjectListState = useRemote(
    curriculumId || null,
    loadSubjectList,
    subjectAttempt,
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
    programStatus: programState.status,
    hasFilters: Object.values(filters).some(Boolean),
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
    retry: () => {
      if (programState.status === "error" || noPrograms)
        setProgramAttempt((value) => value + 1);
      else setSubjectAttempt((value) => value + 1);
    },
  };
}
