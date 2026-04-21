"""API tests for theme endpoints."""

from app.models import Breadcrumb, Tag, Theme, Visibility


# ---------- POST /themes ----------


def test_create_theme_minimal(client):
    response = client.post("/api/themes", json={"body_md": "A new thought"})
    assert response.status_code == 201
    data = response.json()
    assert data["body_md"] == "A new thought"
    assert data["id"] is not None
    assert data["visibility"] == "draft"
    assert data["tags"] == []


def test_create_theme_with_tags(client):
    response = client.post(
        "/api/themes",
        json={
            "body_md": "Python is beautiful",
            "tags": [{"name": "python"}, {"name": "tips"}],
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["body_md"] == "Python is beautiful"
    tag_names = {t["name"] for t in data["tags"]}
    assert tag_names == {"python", "tips"}


def test_create_theme_reuses_existing_tags(client, session):
    client.post(
        "/api/themes", json={"body_md": "First thought", "tags": [{"name": "python"}]}
    )
    response = client.post(
        "/api/themes", json={"body_md": "Second thought", "tags": [{"name": "python"}]}
    )
    assert response.status_code == 201

    from sqlmodel import select

    tags = session.exec(select(Tag).where(Tag.name == "python")).all()
    assert len(tags) == 1


def test_create_theme_normalizes_tag_names(client):
    response = client.post(
        "/api/themes",
        json={"body_md": "Test thought", "tags": [{"name": "My Tag"}]},
    )
    assert response.status_code == 201
    assert response.json()["tags"][0]["name"] == "my-tag"


def test_create_theme_missing_body(client):
    response = client.post("/api/themes", json={})
    assert response.status_code == 422


# ---------- GET /themes ----------


def test_list_themes_empty(client):
    response = client.get("/api/themes")
    assert response.status_code == 200
    assert response.json() == []


def test_list_themes(client):
    client.post("/api/themes", json={"body_md": "Thought A"})
    client.post("/api/themes", json={"body_md": "Thought B"})
    response = client.get("/api/themes")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_themes_filter_by_visibility(client):
    client.post(
        "/api/themes", json={"body_md": "A draft thought", "visibility": "draft"}
    )
    client.post(
        "/api/themes", json={"body_md": "A published thought", "visibility": "published"}
    )
    response = client.get("/api/themes", params={"visibility": "published"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["body_md"] == "A published thought"


def test_list_themes_filter_by_tag(client):
    client.post(
        "/api/themes", json={"body_md": "Tagged thought", "tags": [{"name": "python"}]}
    )
    client.post("/api/themes", json={"body_md": "Untagged thought"})

    response = client.get("/api/themes", params={"tag": "python"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["body_md"] == "Tagged thought"


def test_list_themes_search_by_body(client):
    client.post("/api/themes", json={"body_md": "Python is wonderful"})
    client.post("/api/themes", json={"body_md": "Rust is fast"})

    response = client.get("/api/themes", params={"q": "python"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["body_md"] == "Python is wonderful"


def test_list_themes_search_by_breadcrumb_content(client):
    r = client.post("/api/themes", json={"body_md": "General musings"})
    theme_id = r.json()["id"]
    client.post(
        f"/api/themes/{theme_id}/breadcrumbs",
        json={"body_md": "asyncio is powerful"},
    )

    response = client.get("/api/themes", params={"q": "asyncio"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["body_md"] == "General musings"


def test_list_themes_pagination(client):
    for i in range(5):
        client.post("/api/themes", json={"body_md": f"Thought {i}"})

    response = client.get("/api/themes", params={"limit": 2, "offset": 0})
    assert response.status_code == 200
    assert len(response.json()) == 2

    response = client.get("/api/themes", params={"limit": 2, "offset": 4})
    assert response.status_code == 200
    assert len(response.json()) == 1


# ---------- GET /themes/{id} ----------


def test_get_theme(client):
    r = client.post("/api/themes", json={"body_md": "A retrievable thought"})
    theme_id = r.json()["id"]

    response = client.get(f"/api/themes/{theme_id}")
    assert response.status_code == 200
    assert response.json()["body_md"] == "A retrievable thought"


def test_get_theme_not_found(client):
    response = client.get("/api/themes/999")
    assert response.status_code == 404


# ---------- PUT /themes/{id} ----------


def test_update_theme_body(client):
    r = client.post("/api/themes", json={"body_md": "Original thought"})
    theme_id = r.json()["id"]

    response = client.put(
        f"/api/themes/{theme_id}", json={"body_md": "Revised thought"}
    )
    assert response.status_code == 200
    assert response.json()["body_md"] == "Revised thought"


def test_update_theme_tags(client):
    r = client.post(
        "/api/themes",
        json={"body_md": "Test thought", "tags": [{"name": "old-tag"}]},
    )
    theme_id = r.json()["id"]

    response = client.put(
        f"/api/themes/{theme_id}",
        json={"tags": [{"name": "new-tag"}]},
    )
    assert response.status_code == 200
    tag_names = {t["name"] for t in response.json()["tags"]}
    assert tag_names == {"new-tag"}


def test_update_theme_visibility(client):
    r = client.post("/api/themes", json={"body_md": "Draft thought"})
    theme_id = r.json()["id"]
    assert r.json()["visibility"] == "draft"

    response = client.put(
        f"/api/themes/{theme_id}", json={"visibility": "published"}
    )
    assert response.status_code == 200
    assert response.json()["visibility"] == "published"


def test_update_theme_not_found(client):
    response = client.put("/api/themes/999", json={"body_md": "Nope"})
    assert response.status_code == 404


# ---------- DELETE /themes/{id} ----------


def test_delete_theme(client):
    r = client.post("/api/themes", json={"body_md": "To be deleted"})
    theme_id = r.json()["id"]

    response = client.delete(f"/api/themes/{theme_id}")
    assert response.status_code == 204

    response = client.get(f"/api/themes/{theme_id}")
    assert response.status_code == 404


def test_delete_theme_cascades_to_breadcrumbs(client, session):
    r = client.post("/api/themes", json={"body_md": "Parent thought"})
    theme_id = r.json()["id"]
    client.post(
        f"/api/themes/{theme_id}/breadcrumbs",
        json={"body_md": "Child breadcrumb"},
    )

    client.delete(f"/api/themes/{theme_id}")

    from sqlmodel import select

    breadcrumbs = session.exec(select(Breadcrumb)).all()
    assert len(breadcrumbs) == 0


def test_delete_theme_leaves_tags_intact(client, session):
    """Deleting a theme removes the association but the tag itself survives."""
    r = client.post(
        "/api/themes",
        json={"body_md": "Tagged thought", "tags": [{"name": "keeper"}]},
    )
    theme_id = r.json()["id"]

    client.delete(f"/api/themes/{theme_id}")

    from sqlmodel import select
    from app.models import Tag

    tags = session.exec(select(Tag).where(Tag.name == "keeper")).all()
    assert len(tags) == 1

    response = client.get("/api/tags")
    data = response.json()
    keeper = next(t for t in data if t["name"] == "keeper")
    assert keeper["theme_count"] == 0


def test_delete_theme_not_found(client):
    response = client.delete("/api/themes/999")
    assert response.status_code == 404


# ---------- theme cover image endpoints ----------


def test_generate_theme_image_not_found(client):
    response = client.post("/api/themes/999/generate-image")
    assert response.status_code == 404


def test_commit_theme_image_not_found(client):
    response = client.post(
        "/api/themes/999/image",
        json={"source_url": "https://replicate.delivery/x/out.webp"},
    )
    assert response.status_code == 404


def test_clear_theme_image_not_found(client):
    response = client.delete("/api/themes/999/image")
    assert response.status_code == 404


def test_update_theme_cannot_set_image_url_via_put(client):
    """image_url is not in THEME_UPDATABLE_FIELDS — must use the dedicated endpoints."""
    r = client.post("/api/themes", json={"body_md": "Theme"})
    theme_id = r.json()["id"]

    # Pydantic accepts the field on input but the whitelist rejects it.
    response = client.put(
        f"/api/themes/{theme_id}", json={"image_url": "https://evil.example/x.png"}
    )
    assert response.status_code == 400
    assert "image_url" in response.json()["detail"]


def test_generate_theme_image_missing_token(client, monkeypatch):
    monkeypatch.delenv("REPLICATE_API_TOKEN", raising=False)
    r = client.post("/api/themes", json={"body_md": "Theme"})
    theme_id = r.json()["id"]

    response = client.post(f"/api/themes/{theme_id}/generate-image")
    assert response.status_code == 503
    assert "REPLICATE_API_TOKEN" in response.json()["detail"]


def test_generate_theme_image_happy_path(client, monkeypatch):
    monkeypatch.setenv("REPLICATE_API_TOKEN", "fake-token")
    fake_urls = [f"https://replicate.delivery/x/out-{i}.webp" for i in range(4)]
    monkeypatch.setattr("app.images.replicate.run", lambda *a, **k: fake_urls)

    r = client.post(
        "/api/themes",
        json={"body_md": "On the texture of an afternoon", "tags": [{"name": "slowness"}]},
    )
    theme_id = r.json()["id"]

    response = client.post(f"/api/themes/{theme_id}/generate-image")
    assert response.status_code == 200
    body = response.json()
    assert body["candidates"] == fake_urls
    assert "On the texture of an afternoon" in body["prompt"]
    assert "Mood draws from: slowness" in body["prompt"]


def test_commit_theme_image_rejects_non_replicate_host(client):
    r = client.post("/api/themes", json={"body_md": "Theme"})
    theme_id = r.json()["id"]

    response = client.post(
        f"/api/themes/{theme_id}/image",
        json={"source_url": "https://evil.example/out.webp"},
    )
    assert response.status_code == 400
    assert "allowlist" in response.json()["detail"]


def test_commit_theme_image_rejects_non_https(client):
    r = client.post("/api/themes", json={"body_md": "Theme"})
    theme_id = r.json()["id"]

    response = client.post(
        f"/api/themes/{theme_id}/image",
        json={"source_url": "http://replicate.delivery/x/out.webp"},
    )
    assert response.status_code == 400


def test_commit_theme_image_happy_path(client, monkeypatch, session):
    """Mock commit_image_to_r2 at the api seam to avoid network + R2."""
    monkeypatch.setattr(
        "app.api.commit_image_to_r2",
        lambda url: "https://cdn.example/permanent.webp",
    )

    r = client.post("/api/themes", json={"body_md": "Theme"})
    theme_id = r.json()["id"]

    response = client.post(
        f"/api/themes/{theme_id}/image",
        json={"source_url": "https://replicate.delivery/x/out.webp"},
    )
    assert response.status_code == 200
    assert response.json()["image_url"] == "https://cdn.example/permanent.webp"

    # Persisted on the model.
    session.expire_all()
    refreshed = session.get(Theme, theme_id)
    assert refreshed.image_url == "https://cdn.example/permanent.webp"


def test_clear_theme_image_unsets_field(client, monkeypatch, session):
    monkeypatch.setattr(
        "app.api.commit_image_to_r2",
        lambda url: "https://cdn.example/permanent.webp",
    )
    r = client.post("/api/themes", json={"body_md": "Theme"})
    theme_id = r.json()["id"]
    client.post(
        f"/api/themes/{theme_id}/image",
        json={"source_url": "https://replicate.delivery/x/out.webp"},
    )

    response = client.delete(f"/api/themes/{theme_id}/image")
    assert response.status_code == 200
    assert response.json()["image_url"] is None

    session.expire_all()
    refreshed = session.get(Theme, theme_id)
    assert refreshed.image_url is None
