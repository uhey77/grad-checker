import type { RequirementResult } from "../../domain/entities/requirements.ts";

export interface RequirementMatrixRow {
  id: string;
  requirement: RequirementResult;
  depth: number;
  cells: Partial<Record<RequirementResult["kind"], RequirementResult[]>>;
}

/** 判定値を再計算せず、明示された親・分類だけで表示用の行を組み立てる。 */
export function buildRequirementMatrix(
  requirements: RequirementResult[],
): RequirementMatrixRow[] {
  const byId = new Map(requirements.map((row) => [row.id, row]));
  const selectiveGroups = requirements.filter(
    (row) => row.kind === "selective_group",
  );
  const rows = new Map<string, RequirementMatrixRow>();
  const ownerIds = new Map<string, string>();
  for (const requirement of requirements) {
    if (requirement.kind === "total") continue;
    const parent = requirement.parentId
      ? byId.get(requirement.parentId)
      : undefined;
    // 同じ親・同じ科目分類の必修内訳は、選択必修と同じ科目区分の行へ置く。
    // 親と同じ分類IDを使う複合選択必修群には、区分全体の必修を混ぜない。
    const matchingGroups =
      requirement.kind === "required_courses" &&
      parent?.kind === "classification_total" &&
      requirement.classificationId !== null &&
      requirement.classificationId !== parent.classificationId
        ? selectiveGroups.filter(
            (group) =>
              group.parentId === requirement.parentId &&
              group.classificationId === requirement.classificationId,
          )
        : [];
    const owner =
      matchingGroups.length === 1
        ? matchingGroups[0]
        : (requirement.kind === "required_courses" ||
              requirement.kind === "elective_total") &&
            parent &&
            parent.kind !== "total" &&
            parent.kind !== "required_courses" &&
            parent.kind !== "elective_total" &&
            requirement.classificationId !== null &&
            requirement.classificationId === parent.classificationId
          ? parent
          : requirement;
    ownerIds.set(requirement.id, owner.id);
    if (!rows.has(owner.id)) {
      rows.set(owner.id, {
        id: owner.id,
        requirement: owner,
        depth: 0,
        cells: {},
      });
    }
    const row = rows.get(owner.id)!;
    (row.cells[requirement.kind] ??= []).push(requirement);
  }

  const children = new Map<string | null, RequirementMatrixRow[]>();
  for (const row of rows.values()) {
    let parentId = row.requirement.parentId;
    const visited = new Set([row.id]);
    let ownerId: string | null = null;
    while (parentId && !visited.has(parentId)) {
      visited.add(parentId);
      const candidate = ownerIds.get(parentId);
      if (candidate && candidate !== row.id && rows.has(candidate)) {
        ownerId = candidate;
        break;
      }
      parentId = byId.get(parentId)?.parentId ?? null;
    }
    const siblings = children.get(ownerId) ?? [];
    siblings.push(row);
    children.set(ownerId, siblings);
  }

  const result: RequirementMatrixRow[] = [];
  const emitted = new Set<string>();
  const visit = (row: RequirementMatrixRow, depth: number) => {
    if (emitted.has(row.id)) return;
    emitted.add(row.id);
    result.push({ ...row, depth });
    for (const child of children.get(row.id) ?? []) visit(child, depth + 1);
  };
  for (const row of children.get(null) ?? []) visit(row, 0);
  // 親が欠けた条件・循環した条件も表示から消さない。
  for (const row of rows.values()) visit(row, 0);
  return result;
}
