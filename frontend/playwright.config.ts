import { defineConfig } from "@playwright/test";

const PY = process.env.PYTHON ?? "python";

export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  expect: { timeout: 15_000 },
  use: { baseURL: "http://localhost:3000", trace: "retain-on-failure" },
  webServer: [
    {
      command: `${PY} -m uvicorn main:app --port 8000`,
      cwd: "../backend",
      url: "http://127.0.0.1:8000/api/health",
      env: {
        DATABASE_URL: "sqlite+aiosqlite:///./e2e.db",
        FAKE_LLM: "true",
        COOKIE_SECURE: "false",
        BLOB_BACKEND: "memory",
        SESSION_SECRET: "e2e-secret",
      },
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
    {
      command: "npm run dev -- --port 3000",
      url: "http://localhost:3000",
      env: { BACKEND_DEV_URL: "http://127.0.0.1:8000" },
      reuseExistingServer: !process.env.CI,
      timeout: 120_000,
    },
  ],
  // PW_CHANNEL=chrome uses the locally installed Google Chrome when the Chromium download is blocked.
  projects: [{ name: "chromium", use: { browserName: "chromium", channel: process.env.PW_CHANNEL } }],
});
