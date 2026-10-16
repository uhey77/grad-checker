import { useEffect, useRef, useState } from "react";
import {
  ProfileError,
  type Profile,
  type ProgramOption,
  type ProfileUseCases,
} from "../../modules/profiles/public.ts";

export function useProfile(
  useCases: ProfileUseCases,
  csrf: string,
  expire: () => void,
  latestRevision = 0,
  reportRevision: (revision: number) => void = () => {},
) {
  const [state, setState] = useState<{
    profile: Profile;
    programs: ProgramOption[];
  } | null>(null);
  const [chosenId, setChosenId] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [conflict, setConflict] = useState(false);
  const [confirmReload, setConfirmReload] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const action = useRef<AbortController | null>(null);
  useEffect(() => {
    const controller = new AbortController();
    void Promise.all([
      useCases.getProfile(controller.signal),
      useCases.listPrograms(controller.signal),
    ]).then(
      ([profile, programs]) => {
        if (!controller.signal.aborted) {
          setState({ profile, programs });
          reportRevision(profile.dataRevision);
          setChosenId(profile.curriculumId ?? "");
          setError("");
          setConflict(false);
        }
      },
      (error) => {
        if (!controller.signal.aborted) {
          if (error instanceof ProfileError && error.status === 401) expire();
          setError(
            error instanceof Error
              ? error.message
              : "所属情報を取得できません。",
          );
        }
      },
    );
    return () => {
      controller.abort();
      action.current?.abort();
      action.current = null;
    };
  }, [useCases, attempt, expire, reportRevision]);
  const selected = state?.programs.find((p) => p.curriculumId === chosenId);
  const dirty = !!state && chosenId !== (state.profile.curriculumId ?? "");
  useEffect(() => {
    if (!dirty) return;
    const warn = (event: BeforeUnloadEvent) => {
      event.preventDefault();
      event.returnValue = "";
    };
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [dirty]);
  // 別画面で成績などが保存された場合、未保存の選択がなければ最新を取得し直す。
  const stale = !!state && latestRevision > state.profile.dataRevision;
  useEffect(() => {
    if (!stale || dirty || action.current) return;
    setState(null);
    setNotice("");
    setAttempt((x) => x + 1);
  }, [stale, dirty]);
  async function save() {
    if (!state || !selected || action.current || conflict || !dirty) return;
    const controller = new AbortController();
    action.current = controller;
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const profile = await useCases.saveProgram(
        {
          programId: selected.programId,
          curriculumId: selected.curriculumId,
          expectedRevision: state.profile.dataRevision,
        },
        csrf,
        controller.signal,
      );
      if (!controller.signal.aborted) {
        setState({ ...state, profile });
        reportRevision(profile.dataRevision);
        setNotice("所属を保存しました。");
      }
    } catch (error) {
      if (!controller.signal.aborted) {
        if (error instanceof ProfileError && error.status === 401) expire();
        if (error instanceof ProfileError && error.status === 409)
          setConflict(true);
        setError(
          error instanceof Error ? error.message : "所属を保存できません。",
        );
      }
    } finally {
      if (action.current === controller) action.current = null;
      if (!controller.signal.aborted) setBusy(false);
    }
  }
  function reload() {
    if (action.current) return;
    setConfirmReload(false);
    setState(null);
    setError("");
    setNotice("");
    setAttempt((x) => x + 1);
  }
  return {
    state,
    chosenId,
    selected,
    dirty,
    busy,
    error,
    notice,
    conflict,
    confirmReload,
    confirmRetry: reload,
    cancelRetry: () => setConfirmReload(false),
    choose: (id: string) => {
      setChosenId(id);
      setNotice("");
      setConfirmReload(false);
    },
    save,
    retry: () => {
      if (action.current) return;
      if (dirty) setConfirmReload(true);
      else reload();
    },
  };
}
