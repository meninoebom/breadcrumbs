"""API tests for breadcrumb endpoints."""


# ---------- POST /themes/{id}/breadcrumbs ----------


def test_create_breadcrumb(client):
    r = client.post("/themes", json={"title": "My Theme"})
    theme_id = r.json()["id"]

    response = client.post(
        f"/themes/{theme_id}/breadcrumbs",
        json={"body_md": "A thought"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["body_md"] == "A thought"
    assert data["id"] is not None


def test_create_breadcrumb_invalid_theme(client):
    response = client.post(
        "/themes/999/breadcrumbs",
        json={"body_md": "Orphan"},
    )
    assert response.status_code == 404


def test_create_breadcrumb_missing_body(client):
    r = client.post("/themes", json={"title": "My Theme"})
    theme_id = r.json()["id"]

    response = client.post(
        f"/themes/{theme_id}/breadcrumbs", json={}
    )
    assert response.status_code == 422


# ---------- GET /themes/{id}/breadcrumbs ----------


def test_list_breadcrumbs_empty(client):
    r = client.post("/themes", json={"title": "Empty Theme"})
    theme_id = r.json()["id"]

    response = client.get(f"/themes/{theme_id}/breadcrumbs")
    assert response.status_code == 200
    assert response.json() == []


def test_list_breadcrumbs(client):
    r = client.post("/themes", json={"title": "My Theme"})
    theme_id = r.json()["id"]

    client.post(
        f"/themes/{theme_id}/breadcrumbs",
        json={"body_md": "First"},
    )
    client.post(
        f"/themes/{theme_id}/breadcrumbs",
        json={"body_md": "Second"},
    )

    response = client.get(f"/themes/{theme_id}/breadcrumbs")
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_list_breadcrumbs_invalid_theme(client):
    response = client.get("/themes/999/breadcrumbs")
    assert response.status_code == 404


# ---------- PUT /themes/{id}/breadcrumbs/{id} ----------


def test_update_breadcrumb(client):
    r = client.post("/themes", json={"title": "My Theme"})
    theme_id = r.json()["id"]

    r = client.post(
        f"/themes/{theme_id}/breadcrumbs",
        json={"body_md": "Original"},
    )
    bc_id = r.json()["id"]

    response = client.put(
        f"/themes/{theme_id}/breadcrumbs/{bc_id}",
        json={"body_md": "Updated"},
    )
    assert response.status_code == 200
    assert response.json()["body_md"] == "Updated"


def test_update_breadcrumb_not_found(client):
    r = client.post("/themes", json={"title": "My Theme"})
    theme_id = r.json()["id"]

    response = client.put(
        f"/themes/{theme_id}/breadcrumbs/999",
        json={"body_md": "Nope"},
    )
    assert response.status_code == 404


# ---------- DELETE /themes/{id}/breadcrumbs/{id} ----------


def test_delete_breadcrumb(client):
    r = client.post("/themes", json={"title": "My Theme"})
    theme_id = r.json()["id"]

    r = client.post(
        f"/themes/{theme_id}/breadcrumbs",
        json={"body_md": "To delete"},
    )
    bc_id = r.json()["id"]

    response = client.delete(
        f"/themes/{theme_id}/breadcrumbs/{bc_id}"
    )
    assert response.status_code == 204

    # Verify it's gone
    response = client.get(f"/themes/{theme_id}/breadcrumbs")
    assert len(response.json()) == 0


def test_delete_breadcrumb_not_found(client):
    r = client.post("/themes", json={"title": "My Theme"})
    theme_id = r.json()["id"]

    response = client.delete(
        f"/themes/{theme_id}/breadcrumbs/999"
    )
    assert response.status_code == 404
