import type { RequirementResult } from "../domain/models.ts";

/** 区分合計と、その子孫条件をAPIの表示順で返す。 */
export function filterRequirements(
  requirements: RequirementResult[],
  rootId: string | null,
): RequirementResult[] {
  if (rootId === null) return requirements;
  const byId = new Map(requirements.map((row) => [row.id, row]));
  if (byId.get(rootId)?.kind !== "classification_total") return requirements;
  return requirements.filter((row) => {
    let current: RequirementResult | undefined = row;
    const visited = new Set<string>();
    while (current && !visited.has(current.id)) {
      if (current.id === rootId) return true;
      visited.add(current.id);
      current = current.parentId ? byId.get(current.parentId) : undefined;
    }
    return false;
  });
}
