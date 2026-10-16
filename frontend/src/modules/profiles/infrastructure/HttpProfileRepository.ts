import {
  ProfileError,
  type ProfileRepository,
} from "../application/ProfileUseCases.ts";
import type { ProgramSelection } from "../domain/models.ts";
import { toProfile, toPrograms } from "./mappers.ts";

export class HttpProfileRepository implements ProfileRepository {
  constructor(private readonly base: string) {}
  private async request(
    path: string,
    signal?: AbortSignal,
    payload?: object,
    csrf?: string,
  ): Promise<unknown> {
    try {
      const response = await fetch(this.base + path, {
        method: payload ? "PUT" : "GET",
        credentials: "same-origin",
        cache: "no-store",
        signal,
        headers: payload
          ? { "Content-Type": "application/json", "X-CSRF-Token": csrf ?? "" }
          : undefined,
        body: payload ? JSON.stringify(payload) : undefined,
      });
      let data: unknown;
      try {
        data = await response.json();
      } catch {
        if (signal?.aborted) throw signal.reason;
        throw new ProfileError(
          response.ok ? 502 : response.status,
          "所属サービスの応答を読み込めません。",
        );
      }
      if (!response.ok) {
        const detail =
          data &&
          typeof data === "object" &&
          "detail" in data &&
          typeof data.detail === "string"
            ? data.detail
            : "所属情報の処理に失敗しました。";
        throw new ProfileError(response.status, detail);
      }
      return data;
    } catch (error) {
      if (signal?.aborted || error instanceof ProfileError) throw error;
      throw new ProfileError(
        0,
        "サーバーへ接続できません。時間をおいて再試行してください。",
      );
    }
  }
  async listPrograms(signal?: AbortSignal) {
    return toPrograms(await this.request("/programs", signal));
  }
  async getProfile(signal?: AbortSignal) {
    return toProfile(await this.request("/me", signal));
  }
  async saveProgram(
    selection: ProgramSelection,
    csrf: string,
    signal?: AbortSignal,
  ) {
    return toProfile(
      await this.request(
        "/me/program",
        signal,
        {
          program_id: selection.programId,
          curriculum_id: selection.curriculumId,
          expected_revision: selection.expectedRevision,
        },
        csrf,
      ),
    );
  }
}
