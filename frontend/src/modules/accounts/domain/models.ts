export type AuthSession = {
  student: { id: string; email: string };
  csrfToken: string;
  expiresAt: string;
};

export type AuthPolicy = {
  passwordMinLength: number;
  passwordMaxLength: number;
  verificationMinutes: number;
};
