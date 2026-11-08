// Conventional Commit の変更内容から次の SemVer を決める。
export function nextVersion(previous, messages, initial = '1.0.0') {
  if (previous == null) return initial;
  const match = /^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$/.exec(previous);
  if (!match) throw new Error('Invalid previous version');
  let [, major, minor, patch] = match.map(Number);
  const breaking = messages.some((message) =>
    /^[a-z]+(?:\([^\n)]*\))?!: /i.test(message) ||
    /^[a-z]+(?:\([^\n)]*\))?: BREAKING[ -]CHANGE: /i.test(message) ||
    /^BREAKING[ -]CHANGE: /im.test(message),
  );
  const feature = messages.some((message) => /^feat(?:\([^\n)]*\))?: /i.test(message));
  if (breaking) return `${major + 1}.0.0`;
  if (feature) return `${major}.${minor + 1}.0`;
  return `${major}.${minor}.${patch + 1}`;
}
