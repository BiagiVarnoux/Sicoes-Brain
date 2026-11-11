import unittest
from unittest.mock import AsyncMock, patch

from playwright.async_api import Error, TimeoutError

from monitor import sicoes_nav as nav


class NavigationTests(unittest.IsolatedAsyncioTestCase):
    async def navigate(self, page):
        with patch.object(nav, "_asegurar_portal", new=AsyncMock(return_value=True)):
            await nav.ir_a_buscador(page)

    def page(self, navigation_error=None):
        page = AsyncMock()
        page.evaluate.side_effect = [None, navigation_error, None]
        return page

    async def test_normal_navigation_waits_for_form(self):
        page = self.page()
        await self.navigate(page)
        page.wait_for_selector.assert_awaited_once_with(
            "#formAvanzada", state="attached", timeout=90000)

    async def test_context_destroyed_by_navigation_is_recovered(self):
        page = self.page(Error("Execution context was destroyed, most likely because of a navigation"))
        await self.navigate(page)
        page.wait_for_selector.assert_awaited_once()
        self.assertEqual(page.evaluate.await_count, 3)

    async def test_missing_form_is_a_failure_after_context_loss(self):
        page = self.page(Error("Execution context was destroyed"))
        page.wait_for_selector.side_effect = TimeoutError("form missing")
        with self.assertRaises(TimeoutError):
            await self.navigate(page)
        self.assertEqual(page.evaluate.await_count, 2)

    async def test_other_javascript_errors_are_not_ignored(self):
        page = self.page(Error("irLink is not defined"))
        with self.assertRaisesRegex(Error, "irLink is not defined"):
            await self.navigate(page)
        page.wait_for_selector.assert_not_awaited()
