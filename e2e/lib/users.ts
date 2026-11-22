// Fixture users from app_data/users.yaml (local development only).
const password = process.env.ZENODO_E2E_PASSWORD ?? "123456";

export const users = {
  admin: { email: "admin@zenodo.org", password },
  user: { email: "eu@zenodo.org", password },
};

export type Role = keyof typeof users;
