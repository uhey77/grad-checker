export type AuthSession = {
  student: { id: string; loginName: string };
  csrfToken: string;
  expiresAt: string;
};
