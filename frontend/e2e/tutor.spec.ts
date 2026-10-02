import { expect, test } from "@playwright/test";

test("exercise flow: chat with the tutor and check a structure", async ({ page }) => {
  await page.goto("/");
  const card = page.getByTestId("exercise-ex02");
  await expect(card.getByTestId("unreviewed-badge")).toBeVisible();
  await card.getByRole("button", { name: "Começar" }).click();
  await expect(page).toHaveURL(/\/sessoes\/[0-9a-f-]{36}$/);
  await expect(page.getByRole("heading", { name: "Exercício 2 — C₄H₈O₂" })).toBeVisible();
  await expect(page.locator("[data-testid=spectrum-plot] .main-svg").first()).toBeVisible();

  await page.getByTestId("chat-input").fill("Vejo três sinais.");
  await page.getByRole("button", { name: "Enviar" }).click();
  await expect(page.getByTestId("assistant-message").last()).toContainText("sinal P1");
  await expect(page.getByTestId("tool-chip").first()).toContainText("consultou a lista de picos");

  await page.getByTestId("smiles-input").fill("CCOC(C)=O");
  await page.getByRole("button", { name: "Verificar estrutura" }).click();
  await expect(page.getByTestId("check-formula")).toContainText("C4H8O2");

  await Promise.all([
    page.waitForResponse((r) => r.url().includes("/api/sessions/") && r.request().method() === "PATCH"),
    page.getByRole("button", { name: "Verificação" }).click(),
  ]);
  await page.getByRole("button", { name: "Verificar estrutura" }).click();
  await expect(page.getByText("É a estrutura do exercício.")).toBeVisible();

  await page.reload();
  await expect(page.getByTestId("assistant-message").first()).toContainText("sinal P1");
});

test("custom spectrum: paste peaks and start a session", async ({ page }) => {
  await page.goto("/sessoes/nova");
  await page.getByTestId("peak-paste").fill("4,12 (q, J = 7,1 Hz, 2H), 2,05 (s, 3H), 1,26 (t, J = 7,1 Hz, 3H)");
  await page.getByRole("button", { name: "Interpretar lista" }).click();
  await expect(page.getByTestId("peak-row")).toHaveCount(3);
  await page.getByRole("button", { name: "Começar sessão com o tutor" }).click();
  await expect(page).toHaveURL(/\/sessoes\/[0-9a-f-]{36}$/);
  await expect(page.getByRole("button", { name: "Editar picos" })).toBeVisible();
  await expect(page.locator("[data-testid=spectrum-plot] .main-svg").first()).toBeVisible();
});
