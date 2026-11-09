import type {
  ScreenshotCourse,
  ScreenshotGradeRow,
  ScreenshotReadProgress,
} from "../dto/gradeScreenshot.ts";
import { GradeScreenshotError } from "../errors/GradeScreenshotError.ts";
import type { GradeScreenshotReader } from "../ports/GradeScreenshotReader.ts";
import { parseGradeScreenshotText } from "../services/gradeScreenshot.ts";

// 端末内で読み取れる画像の上限。大きすぎる画像は読み取りに時間がかかるため受け付けない。
export const maxScreenshotBytes = 20 * 1024 * 1024;

// 成績表のスクリーンショットを読み取り、課程の科目と照合した行を返す。保存はしない。
export class ReadGradeScreenshotUseCase {
  constructor(private readonly reader: GradeScreenshotReader) {}

  async execute(
    image: Blob,
    courses: ScreenshotCourse[],
    signal: AbortSignal,
    onProgress?: (progress: ScreenshotReadProgress) => void,
  ): Promise<ScreenshotGradeRow[]> {
    if (!image.type.startsWith("image/"))
      throw new GradeScreenshotError("not_image");
    if (image.size > maxScreenshotBytes)
      throw new GradeScreenshotError("too_large");
    const text = await this.reader.read(image, signal, onProgress);
    const rows = parseGradeScreenshotText(text, courses);
    if (rows.length === 0) throw new GradeScreenshotError("no_rows");
    return rows;
  }
}
