import type { ScreenshotReadProgress } from "../../application/dto/gradeScreenshot.ts";
import { GradeScreenshotError } from "../../application/errors/GradeScreenshotError.ts";
import type { GradeScreenshotReader } from "../../application/ports/GradeScreenshotReader.ts";

// 文字が小さい画像は読み違いが増えるため、この幅を目安に最大2倍まで拡大する。
const targetWidth = 1600;
const maxScale = 2;

function abortError(): DOMException {
  return new DOMException("The operation was aborted.", "AbortError");
}

// 中断されたら待たずに失敗させる。OCRのWorkerは中断時に終了させる。
function untilAborted<T>(promise: Promise<T>, signal: AbortSignal): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    if (signal.aborted) return reject(abortError());
    const onAbort = () => reject(abortError());
    signal.addEventListener("abort", onAbort, { once: true });
    promise.then(
      (value) => {
        signal.removeEventListener("abort", onAbort);
        resolve(value);
      },
      (error: unknown) => {
        signal.removeEventListener("abort", onAbort);
        reject(error);
      },
    );
  });
}

// 小さい画像を拡大し、グレースケールにして読み取りやすくする。使えないブラウザーでは元画像を使う。
async function prepare(image: Blob): Promise<Blob> {
  if (
    typeof createImageBitmap !== "function" ||
    typeof OffscreenCanvas !== "function"
  )
    return image;
  const bitmap = await createImageBitmap(image);
  try {
    const scale = Math.min(maxScale, Math.max(1, targetWidth / bitmap.width));
    const canvas = new OffscreenCanvas(
      Math.round(bitmap.width * scale),
      Math.round(bitmap.height * scale),
    );
    const context = canvas.getContext("2d");
    if (!context) return image;
    context.filter = "grayscale(1)";
    context.imageSmoothingQuality = "high";
    context.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    return await canvas.convertToBlob({ type: "image/png" });
  } finally {
    bitmap.close();
  }
}

// tesseract.jsで端末内のOCRを行う。Worker・WASM・日本語データは同一オリジンから取得する。
export class TesseractGradeScreenshotReader implements GradeScreenshotReader {
  constructor(private readonly assetBase: string) {}

  async read(
    image: Blob,
    signal: AbortSignal,
    onProgress?: (progress: ScreenshotReadProgress) => void,
  ): Promise<string> {
    if (signal.aborted) throw abortError();
    onProgress?.({ stage: "preparing" });
    // 中断・失敗・完了のいずれでも、生成中のWorkerを含めて必ず終了させる。
    let creating: Promise<{ terminate: () => Promise<unknown> }> | null = null;
    try {
      const prepared = await untilAborted(prepare(image), signal);
      // OCRの処理は大きいため、読み取りを始めたときだけ読み込む。
      const { createWorker, OEM } = await untilAborted(
        import("tesseract.js"),
        signal,
      );
      const pending = createWorker("jpn", OEM.LSTM_ONLY, {
        workerPath: `${this.assetBase}/worker.min.js`,
        corePath: this.assetBase,
        langPath: this.assetBase,
        workerBlobURL: false,
        logger: (message) => {
          if (message.status === "recognizing text")
            onProgress?.({ stage: "recognizing", ratio: message.progress });
        },
      });
      creating = pending;
      const worker = await untilAborted(pending, signal);
      const result = await untilAborted(worker.recognize(prepared), signal);
      return result.data.text;
    } catch (error) {
      if (signal.aborted) throw abortError();
      throw new GradeScreenshotError("unreadable", { cause: error });
    } finally {
      void creating?.then(
        (worker) => worker.terminate().catch(() => undefined),
        () => undefined,
      );
    }
  }
}
