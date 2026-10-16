import {
  requestJson,
  type JsonRequest,
} from "../../../shared/infrastructure/http.ts";
import {
  ProfileError,
  type ProfileRepository,
} from "../application/ProfileUseCases.ts";
import type { ProgramSelection } from "../domain/models.ts";
import { toProfile, toPrograms } from "./mappers.ts";

export class HttpProfileRepository implements ProfileRepository {
  constructor(private readonly base: string) {}
  private request(path: string, request: JsonRequest): Promise<unknown> {
    return requestJson(
      this.base + path,
      request,
      (status, message) => new ProfileError(status, message),
      {
        unreadable: "所属サービスの応答を読み込めません。",
        failed: "所属情報の処理に失敗しました。",
      },
    );
  }
  async listPrograms(signal?: AbortSignal) {
    return toPrograms(await this.request("/programs", { signal }));
  }
  async getProfile(signal?: AbortSignal) {
    return toProfile(await this.request("/me", { signal }));
  }
  async saveProgram(
    selection: ProgramSelection,
    csrf: string,
    signal?: AbortSignal,
  ) {
    return toProfile(
      await this.request("/me/program", {
        method: "PUT",
        payload: {
          program_id: selection.programId,
          curriculum_id: selection.curriculumId,
          expected_revision: selection.expectedRevision,
        },
        csrf,
        signal,
      }),
    );
  }
}
