"""API tests for theme endpoints."""

from app.models import Breadcrumb, Tag, Theme, Visibility


# ---------- POST /themes ----------


def test_create_theme_minimal(client):
    response = client.post("/themes", json={"title": "My Theme"})
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "My Theme"
    assert data["id"] is not None
    assert data["visibility"] == "draft"
    assert data["tags"] == []


def test_create_theme_with_tags(client):
    response = client.post(
        "/themes",
        json={
            "title": "Python Tips",
            "description_md": "Useful Python patterns",
            "tags": [{"name": "python"}, {"name": "tips"}],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Python Tips"
    assert data["description_md"] == "Useful Python patterns"
    tag_names = {t["name"] for t in data["tags"]}
    assert tag_names == {"python", "tips"}


def test_create_theme_reuses_existing_tags(client, session):
    # Create a tag first via a theme
    client.post(
        "/themes", json={"title": "Theme 1", "tags": [{"name": "python"}]}
    )
    # Create another theme with the same tag
    response = client.post(
        "/themes", json={"title": "Theme 2", "tags": [{"name": "python"}]}
    )
    assert response.status_code == 201

    # Should be only one "python" tag in the database
    from sqlmodel import select

    tags = session.exec(select(Tag).where(Tag.name == "python")).all()
    assert len(tags) == 1


def test_create_theme_normalizes_tag_names(client):
    response = client.post(
        "/themes",
        json={"title": "Test", "tags": [{"name": "My Tag"}]},
    )
    assert response.status_code == 201
    assert response.json()["tags"][0]["name"] == "my-tag"


def test_create_theme_missing_title(client):
    response = client.post("/themes", json={})
    assert response.status_code == 422


# ---------- GET /themes ----------


def test_list_themes_empty(client):
    response = client.get("/themes")
    assert response.status_code == 200
    assert response.json() == []


def test_list_themes(client):
    client.post("/themes", json={"title": "Theme A"})
    client.post("/themes", json={"title": "Theme B"})
    response = client.get("/themes")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_themes_filter_by_visibility(client):
    client.post(
        "/themes", json={"title": "Draft", "visibility": "draft"}
    )
    client.post(
        "/themes", json={"title": "Published", "visibility": "published"}
    )
    response = client.get("/themes", params={"visibility": "published"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Published"


def test_list_themes_filter_by_tag(client):
    client.post(
        "/themes", json={"title": "Tagged", "tags": [{"name": "python"}]}
    )
    client.post("/themes", json={"title": "Untagged"})

    response = client.get("/themes", params={"tag": "python"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Tagged"


def test_list_themes_search_by_title(client):
    client.post("/themes", json={"title": "Python Tricks"})
    client.post("/themes", json={"title": "Rust Tips"})

    response = client.get("/themes", params={"q": "python"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Python Tricks"


def test_list_themes_search_by_breadcrumb_content(client):
    # Create theme and add breadcrumb
    r = client.post("/themes", json={"title": "General"})
    theme_id = r.json()["id"]
    client.post(
        f"/themes/{theme_id}/breadcrumbs",
        json={"body_md": "asyncio is powerful"},
    )

    response = client.get("/themes", params={"q": "asyncio"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "General"


def test_list_themes_pagination(client):
    for i in range(5):
        client.post("/themes", json={"title": f"Theme {i}"})

    response = client.get("/themes", params={"limit": 2, "offset": 0})
    assert response.status_code == 200
    assert len(response.json()) == 2

    response = client.get("/themes", params={"limit": 2, "offset": 4})
    assert response.status_code == 200
    assert len(response.json()) == 1


# ---------- GET /themes/{id} ----------


def test_get_theme(client):
    r = client.post("/themes", json={"title": "My Theme"})
    theme_id = r.json()["id"]

    response = client.get(f"/themes/{theme_id}")
    assert response.status_code == 200
    assert response.json()["title"] == "My Theme"


def test_get_theme_not_found(client):
    response = client.get("/themes/999")
    assert response.status_code == 404


# ---------- PUT /themes/{id} ----------


def test_update_theme_title(client):
    r = client.post("/themes", json={"title": "Old Title"})
    theme_id = r.json()["id"]

    response = client.put(
        f"/themes/{theme_id}", json={"title": "New Title"}
    )
    assert response.status_code == 200
    assert response.json()["title"] == "New Title"


def test_update_theme_tags(client):
    r = client.post(
        "/themes",
        json={"title": "Test", "tags": [{"name": "old-tag"}]},
    )
    theme_id = r.json()["id"]

    response = client.put(
        f"/themes/{theme_id}",
        json={"tags": [{"name": "new-tag"}]},
    )
    assert response.status_code == 200
    tag_names = {t["name"] for t in response.json()["tags"]}
    assert tag_names == {"new-tag"}


def test_update_theme_visibility(client):
    r = client.post("/themes", json={"title": "Draft Theme"})
    theme_id = r.json()["id"]
    assert r.json()["visibility"] == "draft"

    response = client.put(
        f"/themes/{theme_id}", json={"visibility": "published"}
    )
    assert response.status_code == 200
    assert response.json()["visibility"] == "published"


def test_update_theme_not_found(client):
    response = client.put("/themes/999", json={"title": "Nope"})
    assert response.status_code == 404


# ---------- DELETE /themes/{id} ----------


def test_delete_theme(client):
    r = client.post("/themes", json={"title": "To Delete"})
    theme_id = r.json()["id"]

    response = client.delete(f"/themes/{theme_id}")
    assert response.status_code == 204

    response = client.get(f"/themes/{theme_id}")
    assert response.status_code == 404


def test_delete_theme_cascades_to_breadcrumbs(client, session):
    r = client.post("/themes", json={"title": "Parent"})
    theme_id = r.json()["id"]
    client.post(
        f"/themes/{theme_id}/breadcrumbs",
        json={"body_md": "Child breadcrumb"},
    )

    client.delete(f"/themes/{theme_id}")

    from sqlmodel import select

    breadcrumbs = session.exec(select(Breadcrumb)).all()
    assert len(breadcrumbs) == 0


def test_delete_theme_not_found(client):
    response = client.delete("/themes/999")
    assert response.status_code == 404
