import { AuthUseCases } from "./application/AuthUseCases.ts";
import { HttpAuthRepository } from "./infrastructure/HttpAuthRepository.ts";
export function createAccountsModule(base: string) {
  return new AuthUseCases(new HttpAuthRepository(base));
}
