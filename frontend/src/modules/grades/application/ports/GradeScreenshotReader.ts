import type { ScreenshotReadProgress } from "../dto/gradeScreenshot.ts";

// 画像から文字を読み取る外部機能。読み取りは端末内で行い、画像をサーバーへ送らない。
export interface GradeScreenshotReader {
  // 読み取った全文を行区切りで返す。キャンセルはAbortErrorのまま伝える。
  read(
    image: Blob,
    signal: AbortSignal,
    onProgress?: (progress: ScreenshotReadProgress) => void,
  ): Promise<string>;
}
