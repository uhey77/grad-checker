import { useEffect, useState } from "react";
import {
  ProfileError,
  type Profile,
  type ProgramOption,
  type ProfileUseCases,
} from "../../../../modules/profiles/public.ts";
import { errorMessage } from "../errorMessage.ts";
import { useExclusiveAction } from "../useExclusiveAction.ts";
import { useUnsavedChangesWarning } from "../useUnsavedChangesWarning.ts";

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
  const [editing, setEditing] = useState(false);
  const [conflict, setConflict] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const { busy, running, abort, run } = useExclusiveAction();
  useEffect(() => {
    const controller = new AbortController();
    void Promise.all([
      useCases.getProfile.execute(controller.signal),
      useCases.listPrograms.execute(controller.signal),
    ]).then(
      ([profile, programs]) => {
        if (!controller.signal.aborted) {
          setState({ profile, programs });
          reportRevision(profile.dataRevision);
          setChosenId(profile.curriculumId ?? "");
          setError("");
          setConflict(false);
          setEditing((current) => current || !profile.curriculumId);
        }
      },
      (failure: unknown) => {
        if (!controller.signal.aborted) {
          if (failure instanceof ProfileError && failure.status === 401)
            expire();
          setError(errorMessage(failure, "所属情報を取得できません。"));
        }
      },
    );
    return () => {
      controller.abort();
      abort();
    };
  }, [useCases, attempt, expire, reportRevision, abort]);
  const selected = state?.programs.find((p) => p.curriculumId === chosenId);
  const savedProgram = state?.programs.find(
    (p) => p.curriculumId === state.profile.curriculumId,
  );
  const dirty = !!state && chosenId !== (state.profile.curriculumId ?? "");
  useUnsavedChangesWarning(dirty);
  // 別画面で成績などが保存された場合、未保存の選択がなければ最新を取得し直す。
  const stale = !!state && latestRevision > state.profile.dataRevision;
  useEffect(() => {
    if (!stale || dirty || running()) return;
    // 外部の保存を検知した時点で、読み込み中の表示へ戻して再取得する。
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setState(null);
    setNotice("");
    setAttempt((x) => x + 1);
  }, [stale, dirty, running]);
  async function save() {
    if (!state || !selected || running() || conflict || !dirty) return;
    setError("");
    setNotice("");
    await run(
      (signal) =>
        useCases.saveProgram.execute(
          {
            programId: selected.programId,
            curriculumId: selected.curriculumId,
            expectedRevision: state.profile.dataRevision,
          },
          csrf,
          signal,
        ),
      {
        onSuccess: (profile) => {
          setState({ ...state, profile });
          reportRevision(profile.dataRevision);
          setNotice("所属を保存しました。");
          setEditing(false);
        },
        onError: (failure) => {
          if (failure instanceof ProfileError && failure.status === 401)
            expire();
          if (failure instanceof ProfileError && failure.status === 409) {
            setConflict(true);
            setError(
              "所属情報が更新されています。キャンセルして最新の所属を確認してください。",
            );
          } else {
            setError(errorMessage(failure, "所属を保存できません。"));
          }
        },
      },
    );
  }
  function reload() {
    if (running()) return;
    setState(null);
    setError("");
    setNotice("");
    setAttempt((x) => x + 1);
  }
  return {
    state,
    chosenId,
    selected,
    savedProgram,
    dirty,
    busy,
    error,
    notice,
    editing,
    edit: () => {
      setEditing(true);
      setNotice("");
    },
    conflict,
    choose: (id: string) => {
      setChosenId(id);
      setNotice("");
    },
    save,
    cancel: () => {
      if (running()) return;
      setChosenId(state?.profile.curriculumId ?? "");
      setEditing(false);
      setError("");
      setNotice("");
      if (conflict) reload();
    },
    retry: reload,
  };
}
