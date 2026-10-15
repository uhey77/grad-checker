export type AuthSession = {
  student: { id: string; loginName: string };
  csrfToken: string;
  expiresAt: string;
};

export type AuthPolicy = {
  passwordMinLength: number;
  passwordMaxLength: number;
};
