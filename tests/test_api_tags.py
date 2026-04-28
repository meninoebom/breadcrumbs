"""API tests for tag endpoints."""


# ---------- GET /tags ----------


def test_list_tags_empty(client):
    response = client.get("/api/tags")
    assert response.status_code == 200
    assert response.json() == []


def test_list_tags_with_counts(client):
    # Create themes with tags
    client.post(
        "/api/themes",
        json={"body_md": "Theme 1", "tags": [{"name": "python"}, {"name": "testing"}]},
    )
    client.post(
        "/api/themes",
        json={"body_md": "Theme 2", "tags": [{"name": "python"}]},
    )

    response = client.get("/api/tags")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    # Tags should be alphabetical
    assert data[0]["name"] == "python"
    assert data[1]["name"] == "testing"

    # Python tag used by 2 themes, testing by 1
    assert data[0]["theme_count"] == 2
    assert data[1]["theme_count"] == 1


def test_list_tags_creation_order(client):
    """Tags with no custom position are returned in creation order (position ascending)."""
    client.post(
        "/api/themes",
        json={"body_md": "T", "tags": [{"name": "zebra"}, {"name": "alpha"}]},
    )

    response = client.get("/api/tags")
    data = response.json()
    # zebra was created first (position 1), alpha second (position 2)
    assert data[0]["name"] == "zebra"
    assert data[1]["name"] == "alpha"


# ---------- GET /tags/{name}/themes ----------


def test_get_themes_by_tag(client):
    client.post(
        "/api/themes",
        json={"body_md": "Python Tips", "tags": [{"name": "python"}]},
    )
    client.post(
        "/api/themes",
        json={"body_md": "Rust Tips", "tags": [{"name": "rust"}]},
    )

    response = client.get("/api/tags/python/themes")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["body_md"] == "Python Tips"


def test_get_themes_by_tag_not_found(client):
    response = client.get("/api/tags/nonexistent/themes")
    assert response.status_code == 404


# ---------- PATCH /tags/reorder ----------


def test_reorder_tags_updates_positions(client):
    """Tags are returned in server-side position order after reorder."""
    client.post("/api/themes", json={"body_md": "T1", "tags": [{"name": "alpha"}]})
    client.post("/api/themes", json={"body_md": "T2", "tags": [{"name": "beta"}]})
    client.post("/api/themes", json={"body_md": "T3", "tags": [{"name": "gamma"}]})

    tags_before = client.get("/api/tags").json()
    ids_by_name = {t["name"]: t["id"] for t in tags_before}

    # Reorder: gamma, alpha, beta
    new_order = [ids_by_name["gamma"], ids_by_name["alpha"], ids_by_name["beta"]]
    response = client.patch("/api/tags/reorder", json={"tag_ids": new_order})
    assert response.status_code == 200

    tags_after = client.get("/api/tags").json()
    assert [t["name"] for t in tags_after] == ["gamma", "alpha", "beta"]


def test_reorder_tags_requires_auth(client_no_auth):
    """Reorder endpoint rejects unauthenticated requests."""
    response = client_no_auth.patch("/api/tags/reorder", json={"tag_ids": [1, 2]})
    assert response.status_code == 401


def test_reorder_tags_ignores_unknown_ids(client):
    """Reorder with unknown IDs doesn't crash — unknown IDs are silently skipped."""
    client.post("/api/themes", json={"body_md": "T1", "tags": [{"name": "alpha"}]})
    tags = client.get("/api/tags").json()
    real_id = tags[0]["id"]

    response = client.patch("/api/tags/reorder", json={"tag_ids": [real_id, 99999]})
    assert response.status_code == 200


def test_new_tags_get_highest_position(client):
    """Newly created tags are appended after existing positioned tags."""
    client.post("/api/themes", json={"body_md": "T1", "tags": [{"name": "first"}]})
    client.post("/api/themes", json={"body_md": "T2", "tags": [{"name": "second"}]})

    tags_before = client.get("/api/tags").json()
    ids = [t["id"] for t in tags_before]

    # Fix order: first, second
    client.patch("/api/tags/reorder", json={"tag_ids": ids})

    # Add a new tag
    client.post("/api/themes", json={"body_md": "T3", "tags": [{"name": "newcomer"}]})

    tags_after = client.get("/api/tags").json()
    names = [t["name"] for t in tags_after]
    # newcomer should appear last
    assert names[-1] == "newcomer"
