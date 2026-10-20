import assert from "node:assert/strict";
import { readFile, readdir } from "node:fs/promises";
import { resolve, relative, dirname } from "node:path";
import test from "node:test";
import ts from "typescript";

const root = resolve("src");

// 公開窓口を経由しても、DomainからApplicationへ逆依存させない。
export function publicLayerAllowed(source, exportedLayer) {
  if (!source.startsWith("modules/")) return true;
  const layer = source.split("/")[2];
  if (layer === "domain") return exportedLayer === "domain";
  return ["domain", "application"].includes(exportedLayer);
}

async function publicExports(moduleName) {
  const path = resolve(root, "modules", moduleName, "public.ts");
  const ast = ts.createSourceFile(
    path,
    await readFile(path, "utf8"),
    ts.ScriptTarget.Latest,
    true,
  );
  const layers = new Map();
  for (const node of ast.statements) {
    if (
      ts.isExportDeclaration(node) &&
      node.moduleSpecifier &&
      ts.isStringLiteral(node.moduleSpecifier) &&
      node.exportClause &&
      ts.isNamedExports(node.exportClause)
    ) {
      const layer = node.moduleSpecifier.text.split("/")[1];
      for (const element of node.exportClause.elements)
        layers.set(element.name.text, layer);
    }
  }
  return layers;
}

// ファイル名ではなく、実際のimport/export先と呼出しを解析する。
export function dependencyAllowed(source, target) {
  const parts = source.split("/");
  const ownModule = parts[0] === "modules" ? parts[1] : null;
  const targetParts = target.split("/");
  const uiDirectories = ["components", "hooks", "layouts", "pages"];
  // 業務共通の基盤は自身の中だけを参照し、業務モジュールのinfrastructureだけが利用する。
  if (parts[0] === "shared") return targetParts[0] === "shared";
  if (targetParts[0] === "shared")
    return (
      ownModule !== null &&
      parts[2] === "infrastructure" &&
      targetParts[1] === "infrastructure"
    );
  if (ownModule) {
    if (["app", "App", "main", ...uiDirectories].includes(targetParts[0]))
      return false;
    if (targetParts[0] === "modules" && targetParts[1] !== ownModule)
      return targetParts.length === 3 && targetParts[2] === "public";
    if (parts[2] === "composition") return true;
    const allowed = {
      domain: ["domain"],
      application: ["domain", "application"],
      infrastructure: ["domain", "application", "infrastructure"],
      public: ["domain", "application"],
    };
    return allowed[parts[2]]?.includes(targetParts[2]) ?? false;
  }
  if (uiDirectories.includes(parts[0]) || source === "App") {
    if (source === "hooks/useRemote")
      return targetParts[0] === "hooks" && targetParts.length === 2;
    if (targetParts[0] === "modules")
      return targetParts.length === 3 && targetParts[2] === "public";
    if (
      parts[0] === "components" &&
      ["pages", "app", "App"].includes(targetParts[0])
    )
      return false;
    if (
      parts[0] === "hooks" &&
      ["components", "layouts", "pages", "app", "App"].includes(targetParts[0])
    )
      return false;
    return targetParts[0] !== "main";
  }
  if (parts[0] === "app" && targetParts[0] === "modules")
    return (
      parts[1] === "composition" &&
      targetParts.length === 3 &&
      targetParts[2] === "composition"
    );
  if (source === "main")
    return (
      targetParts[0] === "app" || target === "App" || target === "style.css"
    );

  return true;
}

test("境界検査は逆依存とモジュール内部への直接参照を拒否する", () => {
  assert.equal(
    publicLayerAllowed("modules/requirements/domain/models", "application"),
    false,
  );
  assert.equal(
    publicLayerAllowed("modules/requirements/domain/models", "domain"),
    true,
  );
  assert.equal(
    publicLayerAllowed("modules/requirements/application/evaluate", "domain"),
    true,
  );
  assert.equal(
    dependencyAllowed(
      "modules/subjects/application/list",
      "modules/subjects/infrastructure/http",
    ),
    false,
  );
  assert.equal(
    dependencyAllowed("pages/subjects/page", "modules/grades/application/save"),
    false,
  );
  assert.equal(
    dependencyAllowed(
      "modules/subjects/application/list",
      "app/composition/createApplication",
    ),
    false,
  );
  assert.equal(
    dependencyAllowed("hooks/useRemote", "modules/subjects/public"),
    false,
  );
  assert.equal(dependencyAllowed("App", "modules/subjects/composition"), false);
  assert.equal(
    dependencyAllowed(
      "modules/grades/infrastructure/http",
      "shared/infrastructure/http",
    ),
    true,
  );
  for (const source of [
    "modules/grades/application/save",
    "modules/grades/domain/models",
    "hooks/grades/useGradeEntry",
    "components/grades/GradeTable",
  ])
    assert.equal(
      dependencyAllowed(source, "shared/infrastructure/http"),
      false,
    );
  assert.equal(
    dependencyAllowed("shared/infrastructure/http", "modules/grades/public"),
    false,
  );
  assert.equal(
    dependencyAllowed("pages/grades/page", "modules/subjects/public"),
    true,
  );
  assert.equal(
    dependencyAllowed(
      "app/composition/createApplication",
      "modules/subjects/composition",
    ),
    true,
  );
});

test("全ソースが層・モジュール・アプリ・共通基盤の境界を守る", async () => {
  const contracts = new Map();
  for (const moduleName of await readdir(resolve(root, "modules")))
    contracts.set(moduleName, await publicExports(moduleName));
  async function scan(directory) {
    for (const entry of await readdir(directory, { withFileTypes: true })) {
      const path = resolve(directory, entry.name);
      if (entry.isDirectory()) {
        await scan(path);
        continue;
      }
      if (!/\.tsx?$/.test(path)) continue;
      const source = relative(root, path).replace(/\.tsx?$/, "");
      const ast = ts.createSourceFile(
        path,
        await readFile(path, "utf8"),
        ts.ScriptTarget.Latest,
        true,
      );
      const layer = source.startsWith("modules/")
        ? source.split("/")[2]
        : source.split("/")[1];
      function visit(node) {
        const specifier =
          ts.isImportDeclaration(node) || ts.isExportDeclaration(node)
            ? node.moduleSpecifier
            : ts.isCallExpression(node) &&
                node.expression.kind === ts.SyntaxKind.ImportKeyword
              ? node.arguments[0]
              : null;
        if (specifier && ts.isStringLiteral(specifier)) {
          const dependency = specifier.text;
          if (dependency.startsWith(".")) {
            const target = relative(
              root,
              resolve(dirname(path), dependency),
            ).replace(/\.tsx?$/, "");
            assert.ok(
              dependencyAllowed(source, target),
              `${source} → ${target}`,
            );
            const sourceParts = source.split("/");
            const targetParts = target.split("/");
            if (
              sourceParts[0] === "modules" &&
              targetParts[0] === "modules" &&
              sourceParts[1] !== targetParts[1]
            ) {
              const bindings = ts.isImportDeclaration(node)
                ? node.importClause?.namedBindings
                : ts.isExportDeclaration(node)
                  ? node.exportClause
                  : null;
              assert.ok(
                bindings &&
                  (ts.isNamedImports(bindings) || ts.isNamedExports(bindings)),
                `${source}: モジュール間は名前付きの公開契約を使う`,
              );
              for (const element of bindings.elements) {
                const name = (element.propertyName ?? element.name).text;
                const exportedLayer = contracts.get(targetParts[1])?.get(name);
                assert.ok(
                  publicLayerAllowed(source, exportedLayer),
                  `${source} → ${target}.${name} (${exportedLayer})`,
                );
              }
            }
          } else if (
            layer === "domain" ||
            layer === "application" ||
            source.startsWith("shared/")
          ) {
            assert.ok(
              !/^(react(?:-dom)?)(\/|$)/.test(dependency),
              `${source} → ${dependency}`,
            );
          }
        }
        if (
          ts.isCallExpression(node) &&
          ts.isIdentifier(node.expression) &&
          node.expression.text === "fetch"
        )
          assert.equal(
            layer,
            "infrastructure",
            `${source}: fetchはinfrastructureに限定する`,
          );
        ts.forEachChild(node, visit);
      }
      visit(ast);
    }
  }
  await scan(root);
});
