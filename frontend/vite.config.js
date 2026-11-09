import { createReadStream, existsSync, readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

const proxy = {
  "/api": {
    target: process.env.API_PROXY_TARGET || "http://127.0.0.1:8000",
    changeOrigin: false,
  },
  "^/(docs|openapi\\.json)$": {
    target: process.env.API_PROXY_TARGET || "http://127.0.0.1:8000",
    changeOrigin: false,
  },
};

// スクリーンショットのOCRで使うWorker・WASM・日本語データ。外部CDNを使わず同一オリジンの/ocrから配信する。
// コアはWorkerがSIMD対応を判定して1つだけ取得する。
const ocrAssets = {
  "worker.min.js": "tesseract.js/dist/worker.min.js",
  "tesseract-core-lstm.wasm.js":
    "tesseract.js-core/tesseract-core-lstm.wasm.js",
  "tesseract-core-simd-lstm.wasm.js":
    "tesseract.js-core/tesseract-core-simd-lstm.wasm.js",
  "tesseract-core-relaxedsimd-lstm.wasm.js":
    "tesseract.js-core/tesseract-core-relaxedsimd-lstm.wasm.js",
  "jpn.traineddata.gz":
    "@tesseract.js-data/jpn/4.0.0_best_int/jpn.traineddata.gz",
};

function ocrAssetPath(name) {
  const path = fileURLToPath(
    new URL(`./node_modules/${ocrAssets[name]}`, import.meta.url),
  );
  if (!existsSync(path)) throw new Error(`OCR asset not found: ${path}`);
  return path;
}

function ocrAssetsPlugin() {
  return {
    name: "grad-checker-ocr-assets",
    configureServer(server) {
      server.middlewares.use("/ocr", (request, response, next) => {
        const name = (request.url ?? "").split("?")[0].replace(/^\//, "");
        if (!Object.hasOwn(ocrAssets, name)) return next();
        response.setHeader(
          "Content-Type",
          name.endsWith(".js") ? "text/javascript" : "application/octet-stream",
        );
        createReadStream(ocrAssetPath(name)).pipe(response);
      });
    },
    generateBundle() {
      for (const name of Object.keys(ocrAssets))
        this.emitFile({
          type: "asset",
          fileName: `ocr/${name}`,
          source: readFileSync(ocrAssetPath(name)),
        });
    },
  };
}

export default defineConfig({
  plugins: [ocrAssetsPlugin()],
  server: { proxy },
  preview: { proxy },
});
