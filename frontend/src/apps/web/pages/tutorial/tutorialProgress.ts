const keyFor = (studentId: string) =>
  `grad-checker.tutorial.completed.${studentId}`;

export function tutorialCompleted(studentId: string): boolean {
  try {
    return window.localStorage.getItem(keyFor(studentId)) === "1";
  } catch {
    return false;
  }
}

export function completeTutorial(studentId: string): void {
  try {
    window.localStorage.setItem(keyFor(studentId), "1");
  } catch {
    // ストレージを使えない場合もアプリを利用できる。
  }
}
