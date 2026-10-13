import { test, expect } from "@playwright/test";
import AxeBuilder from "@axe-core/playwright";

test("navigation recording loads, plays and seeks without downloading on page load", async ({ page }, testInfo) => {
  const requested = [];
  page.on("request", (request) => {
    if (request.url().endsWith(".mp4")) requested.push(request.url());
  });
  await page.goto("/#demo");
  const video = page.locator("#demo video");
  await expect(video).toBeVisible();
  expect(requested).toEqual([]);
  await video.evaluate((element) => element.load());
  await expect.poll(() => video.evaluate((element) => element.readyState)).toBeGreaterThanOrEqual(2);
  const duration = await video.evaluate((element) => element.duration);
  expect(duration).toBeGreaterThan(68);
  expect(duration).toBeLessThan(70);
  await video.evaluate((element) => element.play());
  await expect.poll(() => video.evaluate((element) => element.currentTime)).toBeGreaterThan(0.3);
  await video.evaluate((element) => { element.pause(); element.currentTime = 60; });
  await expect.poll(() => video.evaluate((element) => element.seeking)).toBe(false);
  await page.locator("#demo").screenshot({ path: testInfo.outputPath("navigation-video.png") });
  await expect(page.locator("#demo-description")).toContainText("A* navigation simulation");
});

test("project page renders the actual robot and supports its exploration controls", async ({
  page,
}, testInfo) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/");
  await expect(page.locator(".three-mount")).toHaveAttribute(
    "data-model-status",
    "ready",
    { timeout: 30000 },
  );
  await expect(page.getByRole("heading", { level: 1 })).toContainText(
    "A body for",
  );
  await page.screenshot({
    path: testInfo.outputPath("desktop.png"),
    fullPage: true,
  });
  const initial = await page.locator(".three-mount canvas").screenshot();
  await page.getByRole("button", { name: "front", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "front", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
  const front = await page.locator(".three-mount canvas").screenshot();
  expect(front.equals(initial)).toBe(false);
  await page.getByRole("button", { name: "Toggle wireframe" }).click();
  expect(
    (await page.locator(".three-mount canvas").screenshot()).equals(front),
  ).toBe(false);
  await page.getByRole("button", { name: "Toggle wireframe" }).click();
  await page.getByRole("button", { name: "Reset model view" }).click();
  await expect(page.getByRole("button", { name: "3D view" })).toHaveAttribute(
    "aria-pressed",
    "true",
  );
  await page.getByRole("tab", { name: /Dual arms/ }).click();
  await expect(page.getByRole("tabpanel")).toContainText(
    "5 positioning axes + gripper",
  );
  await page.getByRole("tab", { name: /Dual arms/ }).press("ArrowRight");
  await expect(page.getByRole("tab", { name: /Modular tower/ })).toBeFocused();
  await expect(page.getByRole("tabpanel")).toContainText("204 × 204 mm");
  await page.getByText("Is the 3D model the finished physical robot?").click();
  await expect(page.locator("details[open]")).toContainText(
    "Some geometry, masses and hardware limits are estimates",
  );
  const downloadEvent = page.waitForEvent("download");
  await page.locator(".resource-row[download]").click();
  expect((await downloadEvent).suggestedFilename()).toBe("Underbot-R08.zip");
  const report = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(
    report.violations.map((v) => ({
      id: v.id,
      nodes: v.nodes.map((n) => n.target),
    })),
  ).toEqual([]);
  expect(errors).toEqual([]);
});

test("layout fits small phones, tablets and desktop; mobile navigation works", async ({
  page,
}, testInfo) => {
  await page.goto("/");
  await expect(page.locator(".three-mount")).toHaveAttribute(
    "data-model-status",
    "ready",
    { timeout: 30000 },
  );
  for (const width of [320, 390, 600, 768, 1024, 1440]) {
    await page.setViewportSize({ width, height: 900 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBe(true);
  }
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: testInfo.outputPath("mobile.png"),
    fullPage: true,
  });
  await page.getByRole("button", { name: "Open menu" }).click();
  await expect(page.getByRole("navigation")).toBeVisible();
  await page
    .getByRole("navigation")
    .getByRole("link", { name: "Hardware" })
    .click();
  await expect(page.getByRole("button", { name: "Open menu" })).toHaveAttribute(
    "aria-expanded",
    "false",
  );
  await expect(page).toHaveURL(/#hardware$/);
  const report = await new AxeBuilder({ page })
    .withTags(["wcag2a", "wcag2aa", "wcag21aa"])
    .analyze();
  expect(
    report.violations.map((v) => ({
      id: v.id,
      nodes: v.nodes.map((n) => n.target),
    })),
  ).toEqual([]);
});

test("explorer loads joint controls, mimic behavior and legacy dashboard URL", async ({
  page,
}, testInfo) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto("/explorer");
  const frame = page.frameLocator("iframe");
  // Use the delivered model's joint naming rather than assuming a runtime controller.
  await expect(frame.locator("input[type=range]")).toHaveCount(16);
  const viewerFrame = page
    .frames()
    .find((f) => f.url().includes("/model/viewer.html"));
  const result = await viewerFrame.evaluate(() => {
    const viewer = window.underbotViewer;
    const mimic = viewer.data.joints.find((j) => j.mimic);
    viewer.setJoint(mimic.mimic.joint, 0.2);
    return {
      value: viewer.getMimicValue(mimic.name),
      expected: 0.2 * mimic.mimic.multiplier + mimic.mimic.offset,
    };
  });
  expect(result.value).toBeCloseTo(result.expected);
  const firstSlider = frame.locator("input[type=range]").first();
  await firstSlider.focus();
  await firstSlider.press("ArrowRight");
  await expect(firstSlider).not.toHaveValue("0");
  await frame.getByRole("button", { name: "Reset joints" }).click();
  await expect(firstSlider).toHaveValue("0");
  await page.screenshot({
    path: testInfo.outputPath("explorer.png"),
    fullPage: true,
  });
  await page.goto("/dashboard");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Meet the moving parts.",
  );
  expect(await page.locator("body").innerText()).not.toContain(
    "Live Monitoring",
  );
  expect(errors).toEqual([]);
});

test("a failed model download leaves a useful image and package link", async ({
  page,
}) => {
  await page.route("**/model/robot.json", (route) => route.abort());
  await page.goto("/");
  await expect(page.locator(".robot-error")).toBeVisible();
  await expect(page.locator(".robot-error img")).toBeVisible();
  await expect(page.locator(".robot-error a")).toHaveAttribute(
    "href",
    "/model/Underbot-R08.zip",
  );
});
