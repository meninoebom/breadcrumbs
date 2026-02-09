"""API tests for tag endpoints."""


# ---------- GET /tags ----------


def test_list_tags_empty(client):
    response = client.get("/tags")
    assert response.status_code == 200
    assert response.json() == []


def test_list_tags_with_counts(client):
    # Create themes with tags
    client.post(
        "/themes",
        json={"title": "Theme 1", "tags": [{"name": "python"}, {"name": "testing"}]},
    )
    client.post(
        "/themes",
        json={"title": "Theme 2", "tags": [{"name": "python"}]},
    )

    response = client.get("/tags")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2

    # Tags should be alphabetical
    assert data[0]["name"] == "python"
    assert data[1]["name"] == "testing"

    # Python tag used by 2 themes, testing by 1
    assert data[0]["theme_count"] == 2
    assert data[1]["theme_count"] == 1


def test_list_tags_alphabetical_order(client):
    client.post(
        "/themes",
        json={"title": "T", "tags": [{"name": "zebra"}, {"name": "alpha"}]},
    )

    response = client.get("/tags")
    data = response.json()
    assert data[0]["name"] == "alpha"
    assert data[1]["name"] == "zebra"


# ---------- GET /tags/{name}/themes ----------


def test_get_themes_by_tag(client):
    client.post(
        "/themes",
        json={"title": "Python Tips", "tags": [{"name": "python"}]},
    )
    client.post(
        "/themes",
        json={"title": "Rust Tips", "tags": [{"name": "rust"}]},
    )

    response = client.get("/tags/python/themes")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Python Tips"


def test_get_themes_by_tag_not_found(client):
    response = client.get("/tags/nonexistent/themes")
    assert response.status_code == 404
