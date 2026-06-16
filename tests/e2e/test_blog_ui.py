import re

import pytest
from playwright.sync_api import Page, expect


def _login(page: Page, base_url: str, username: str, password: str) -> None:
    page.goto(f"{base_url}/admin/login")
    page.fill("#username", username)
    page.fill("#password", password)
    page.get_by_role("button", name="Log in").click()
    expect(page).to_have_url(re.compile(r".*/admin/?$"))
    expect(page.get_by_role("heading", name="Admin Dashboard")).to_be_visible()


@pytest.mark.e2e
def test_admin_login_logout(
    page: Page,
    base_url: str,
    admin_username: str,
    admin_password: str,
) -> None:
    _login(page, base_url, admin_username, admin_password)

    page.get_by_role("link", name="Log out").click()
    expect(page).to_have_url(re.compile(r".*/admin/login$"))
    expect(page.get_by_role("heading", name="Admin Login")).to_be_visible()


@pytest.mark.e2e
def test_admin_crud_and_public_pages(
    page: Page,
    base_url: str,
    admin_username: str,
    admin_password: str,
    unique_post: dict[str, str],
) -> None:
    _login(page, base_url, admin_username, admin_password)

    # Create post
    page.get_by_role("link", name="+ New Post").click()
    expect(page.get_by_role("heading", name="New Post")).to_be_visible()
    page.fill("#title", unique_post["title"])
    page.fill("#content", unique_post["content"])
    page.get_by_role("button", name="Create Post").click()

    expect(page.get_by_text("Post created successfully.")).to_be_visible()
    created_row = page.locator("tr", has_text=unique_post["title"]).first
    expect(created_row).to_be_visible()

    # Public home page includes the new post
    page.goto(f"{base_url}/")
    expect(page.get_by_role("heading", name="Latest Posts")).to_be_visible()
    expect(page.get_by_role("link", name=unique_post["title"])).to_be_visible()

    # Specific blog post page
    page.get_by_role("link", name=unique_post["title"]).click()
    expect(page.get_by_role("heading", name=unique_post["title"])).to_be_visible()
    expect(page.get_by_text("This post was created by Playwright.")).to_be_visible()

    # Edit post
    page.goto(f"{base_url}/admin/")
    editable_row = page.locator("tr", has_text=unique_post["title"]).first
    editable_row.get_by_role("link", name="Edit").click()
    expect(page.get_by_role("heading", name="Edit Post")).to_be_visible()
    page.fill("#title", unique_post["updated_title"])
    page.fill("#content", unique_post["updated_content"])
    page.get_by_role("button", name="Save Changes").click()

    expect(page.get_by_text("Post updated successfully.")).to_be_visible()
    expect(page.locator("tr", has_text=unique_post["updated_title"]).first).to_be_visible()

    # Updated title appears on home page
    page.goto(f"{base_url}/")
    expect(page.get_by_role("link", name=unique_post["updated_title"])).to_be_visible()

    # Delete post
    page.goto(f"{base_url}/admin/")
    deletable_row = page.locator("tr", has_text=unique_post["updated_title"]).first
    page.once("dialog", lambda dialog: dialog.accept())
    deletable_row.get_by_role("button", name="Delete").click()

    expect(page.get_by_text("Post deleted.")).to_be_visible()
    expect(page.locator("tr", has_text=unique_post["updated_title"])).to_have_count(0)

    # Deleted post should no longer be listed on home page
    page.goto(f"{base_url}/")
    expect(page.get_by_role("link", name=unique_post["updated_title"])).to_have_count(0)
