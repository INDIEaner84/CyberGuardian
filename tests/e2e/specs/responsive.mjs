// Small screens: nothing may run off the edge or collide, in every style world.
import assert from 'node:assert/strict';
import { test } from '../lib/harness.mjs';
import { MOBILE, TABLET, THEMES, VIEWS, assertClean, chooseTheme, enterCockpit, horizontalOverflow, openView, overlappingPairs } from '../lib/app.mjs';

const LANDING_HEADER = ['.landing-topline .brand-lockup', '.landing-topline .landing-status', '.landing-topline .theme-switch'];
const TOPBAR = ['#backToStart', '.topbar .brand-lockup--compact', '#viewCrumb', '.topbar .sync-chip', '.topbar .clock', '.topbar .theme-switch', '#motionToggle'];

for (const theme of THEMES) {
  test(`responsive: ${theme} at 390 px — landing and every cockpit view stay inside the viewport`, async ({ open }) => {
    const handle = await open({ theme, viewport: MOBILE });
    const { page } = handle;
    assert.deepEqual(await overlappingPairs(page, LANDING_HEADER), [], 'landing header controls do not collide');
    assert.deepEqual(await horizontalOverflow(page), [], 'landing page');
    await enterCockpit(page);
    assert.deepEqual(await overlappingPairs(page, TOPBAR), [], 'cockpit topbar controls do not collide');
    for (const view of VIEWS) {
      await openView(page, view);
      assert.deepEqual(await horizontalOverflow(page), [], `${view} view`);
    }
    await assertClean(handle);
  }, { timeout: 90_000 });
}

test('responsive: tablet width keeps the topbar and command deck intact in every world', async ({ open }) => {
  const handle = await open({ theme: 'nightwatch', viewport: TABLET });
  const { page } = handle;
  await enterCockpit(page);
  for (const theme of THEMES) {
    await chooseTheme(page, theme, '.topbar');
    assert.deepEqual(await overlappingPairs(page, TOPBAR), [], `${theme}: topbar`);
    assert.deepEqual(await horizontalOverflow(page), [], `${theme}: command deck`);
  }
  await assertClean(handle);
}, { timeout: 90_000 });
