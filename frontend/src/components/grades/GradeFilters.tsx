import type {
  CatalogCategory,
  CatalogFilters,
} from "../../modules/subjects/public.ts";
import type { GradeFilters as Filters } from "../../modules/grades/public.ts";
import { courseStatusLabels, termLabels } from "./labels";

type Key = keyof (CatalogFilters & Filters);

// 子の区分を親の直後に並べ、字下げで階層を示す。
function treeOrder(categories: CatalogCategory[]): CatalogCategory[] {
  const ordered: CatalogCategory[] = [];
  const visit = (parentId: string | null) => {
    for (const category of categories
      .filter((c) => c.parentId === parentId)
      .sort((a, b) => a.displayOrder - b.displayOrder)) {
      ordered.push(category);
      visit(category.id);
    }
  };
  visit(null);
  return ordered;
}

export function GradeFilters({
  filters,
  categories,
  faculties,
  departments,
  years,
  changeFilter,
}: {
  filters: CatalogFilters & Filters;
  categories: CatalogCategory[];
  faculties: string[];
  departments: string[];
  years: number[];
  changeFilter: (key: Key, value: string) => void;
}) {
  const select = (
    key: Key,
    label: string,
    options: [string, string][],
    disabled = false,
  ) => (
    <div>
      <label htmlFor={`grade-filter-${key}`}>{label}</label>
      <select
        id={`grade-filter-${key}`}
        value={filters[key]}
        disabled={disabled}
        onChange={(event) => changeFilter(key, event.target.value)}
      >
        <option value="">すべて</option>
        {options.map(([value, text]) => (
          <option key={value} value={value}>
            {text}
          </option>
        ))}
      </select>
    </div>
  );
  return (
    <div className="filters grade-filters">
      <div className="search-field">
        <label htmlFor="grade-filter-search">科目名・科目コードを検索</label>
        <input
          id="grade-filter-search"
          type="search"
          placeholder="例：プログラミング、CS-C001"
          value={filters.search}
          onChange={(event) => changeFilter("search", event.target.value)}
        />
      </div>
      {select(
        "categoryId",
        "科目区分（本人課程）",
        treeOrder(categories).map((c) => [
          c.id,
          `${"　".repeat(c.level)}${c.name}`,
        ]),
      )}
      {select(
        "faculty",
        "開講学部",
        faculties.map((name) => [name, name]),
      )}
      {select(
        "department",
        "開講学科",
        departments.map((name) => [name, name]),
        departments.length === 0,
      )}
      {select("semester", "開講学期", [
        ["first", "前期"],
        ["second", "後期"],
      ])}
      {select("status", "修得状況", Object.entries(courseStatusLabels))}
      {select(
        "year",
        "履修年度",
        years.map((year) => [String(year), `${year}年度`]),
        years.length === 0,
      )}
      {select("term", "履修学期", Object.entries(termLabels))}
    </div>
  );
}
