"""API tests for breadcrumb endpoints."""


# ---------- POST /themes/{id}/breadcrumbs ----------


def test_create_breadcrumb(client):
    r = client.post("/themes", json={"body_md": "My Theme"})
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
    r = client.post("/themes", json={"body_md": "My Theme"})
    theme_id = r.json()["id"]

    response = client.post(
        f"/themes/{theme_id}/breadcrumbs", json={}
    )
    assert response.status_code == 422


# ---------- GET /themes/{id}/breadcrumbs ----------


def test_list_breadcrumbs_empty(client):
    r = client.post("/themes", json={"body_md": "Empty Theme"})
    theme_id = r.json()["id"]

    response = client.get(f"/themes/{theme_id}/breadcrumbs")
    assert response.status_code == 200
    assert response.json() == []


def test_list_breadcrumbs(client):
    r = client.post("/themes", json={"body_md": "My Theme"})
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
    r = client.post("/themes", json={"body_md": "My Theme"})
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
    r = client.post("/themes", json={"body_md": "My Theme"})
    theme_id = r.json()["id"]

    response = client.put(
        f"/themes/{theme_id}/breadcrumbs/999",
        json={"body_md": "Nope"},
    )
    assert response.status_code == 404


# ---------- DELETE /themes/{id}/breadcrumbs/{id} ----------


def test_delete_breadcrumb(client):
    r = client.post("/themes", json={"body_md": "My Theme"})
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
    r = client.post("/themes", json={"body_md": "My Theme"})
    theme_id = r.json()["id"]

    response = client.delete(
        f"/themes/{theme_id}/breadcrumbs/999"
    )
    assert response.status_code == 404


# ---------- theme-mismatch guards ----------


def test_update_breadcrumb_wrong_theme(client):
    """PUT a breadcrumb via a different theme's URL returns 404."""
    r1 = client.post("/themes", json={"body_md": "Theme A"})
    r2 = client.post("/themes", json={"body_md": "Theme B"})
    theme_a_id = r1.json()["id"]
    theme_b_id = r2.json()["id"]

    r = client.post(
        f"/themes/{theme_a_id}/breadcrumbs",
        json={"body_md": "Belongs to A"},
    )
    bc_id = r.json()["id"]

    response = client.put(
        f"/themes/{theme_b_id}/breadcrumbs/{bc_id}",
        json={"body_md": "Sneaky update"},
    )
    assert response.status_code == 404


def test_delete_breadcrumb_wrong_theme(client):
    """DELETE a breadcrumb via a different theme's URL returns 404."""
    r1 = client.post("/themes", json={"body_md": "Theme A"})
    r2 = client.post("/themes", json={"body_md": "Theme B"})
    theme_a_id = r1.json()["id"]
    theme_b_id = r2.json()["id"]

    r = client.post(
        f"/themes/{theme_a_id}/breadcrumbs",
        json={"body_md": "Belongs to A"},
    )
    bc_id = r.json()["id"]

    response = client.delete(f"/themes/{theme_b_id}/breadcrumbs/{bc_id}")
    assert response.status_code == 404

    # Breadcrumb should still exist under the correct theme
    response = client.get(f"/themes/{theme_a_id}/breadcrumbs")
    assert len(response.json()) == 1


# ---------- parent-child breadcrumbs ----------


def test_create_breadcrumb_with_parent(client):
    """POST with parent_id creates a child breadcrumb."""
    r = client.post("/themes", json={"body_md": "My Theme"})
    theme_id = r.json()["id"]

    # Create parent
    r = client.post(
        f"/themes/{theme_id}/breadcrumbs",
        json={"body_md": "Parent thought"},
    )
    parent_id = r.json()["id"]
    assert r.json()["parent_id"] is None

    # Create child
    r = client.post(
        f"/themes/{theme_id}/breadcrumbs",
        json={"body_md": "Child thought", "parent_id": parent_id},
    )
    assert r.status_code == 201
    assert r.json()["parent_id"] == parent_id


def test_create_breadcrumb_invalid_parent(client):
    """POST with nonexistent parent_id returns 400."""
    r = client.post("/themes", json={"body_md": "My Theme"})
    theme_id = r.json()["id"]

    r = client.post(
        f"/themes/{theme_id}/breadcrumbs",
        json={"body_md": "Orphan", "parent_id": 9999},
    )
    assert r.status_code == 400
    assert "not found" in r.json()["detail"].lower()


def test_create_breadcrumb_cross_theme_parent(client):
    """POST with parent_id from a different theme returns 400."""
    r1 = client.post("/themes", json={"body_md": "Theme A"})
    r2 = client.post("/themes", json={"body_md": "Theme B"})
    theme_a_id = r1.json()["id"]
    theme_b_id = r2.json()["id"]

    # Create breadcrumb in theme A
    r = client.post(
        f"/themes/{theme_a_id}/breadcrumbs",
        json={"body_md": "In theme A"},
    )
    bc_a_id = r.json()["id"]

    # Try to create child in theme B with parent in theme A
    r = client.post(
        f"/themes/{theme_b_id}/breadcrumbs",
        json={"body_md": "Cross-theme child", "parent_id": bc_a_id},
    )
    assert r.status_code == 400
    assert "different theme" in r.json()["detail"].lower()


def test_create_breadcrumb_at_max_depth(client):
    """A chain of depth 9 (10 nodes) is accepted; depth 10 (11 nodes) is rejected."""
    r = client.post("/themes", json={"body_md": "Deep Theme"})
    theme_id = r.json()["id"]

    # Build a chain of 10 nodes (depth 9 — the new node is the 10th)
    parent_id = None
    for i in range(10):
        payload = {"body_md": f"Level {i}"}
        if parent_id is not None:
            payload["parent_id"] = parent_id
        r = client.post(f"/themes/{theme_id}/breadcrumbs", json=payload)
        assert r.status_code == 201, f"Level {i} should be accepted"
        parent_id = r.json()["id"]

    # The 11th node (depth 10) should be rejected
    r = client.post(
        f"/themes/{theme_id}/breadcrumbs",
        json={"body_md": "Too deep", "parent_id": parent_id},
    )
    assert r.status_code == 400
    assert "depth" in r.json()["detail"].lower()


def test_delete_parent_cascades_children(client):
    """Deleting a parent breadcrumb also deletes its children."""
    r = client.post("/themes", json={"body_md": "My Theme"})
    theme_id = r.json()["id"]

    # Create parent
    r = client.post(
        f"/themes/{theme_id}/breadcrumbs",
        json={"body_md": "Parent"},
    )
    parent_id = r.json()["id"]

    # Create child
    client.post(
        f"/themes/{theme_id}/breadcrumbs",
        json={"body_md": "Child", "parent_id": parent_id},
    )

    # Delete parent
    r = client.delete(f"/themes/{theme_id}/breadcrumbs/{parent_id}")
    assert r.status_code == 204

    # Both should be gone
    r = client.get(f"/themes/{theme_id}/breadcrumbs")
    assert len(r.json()) == 0


def test_list_breadcrumbs_includes_parent_id(client):
    """GET list includes parent_id field (null for top-level)."""
    r = client.post("/themes", json={"body_md": "My Theme"})
    theme_id = r.json()["id"]

    # Create parent
    r = client.post(
        f"/themes/{theme_id}/breadcrumbs",
        json={"body_md": "Parent"},
    )
    parent_id = r.json()["id"]

    # Create child
    client.post(
        f"/themes/{theme_id}/breadcrumbs",
        json={"body_md": "Child", "parent_id": parent_id},
    )

    r = client.get(f"/themes/{theme_id}/breadcrumbs")
    assert r.status_code == 200
    items = r.json()
    assert len(items) == 2

    parent_item = next(i for i in items if i["id"] == parent_id)
    child_item = next(i for i in items if i["id"] != parent_id)

    assert parent_item["parent_id"] is None
    assert child_item["parent_id"] == parent_id


def test_update_breadcrumb_ignores_parent_id(client):
    """PUT does not change parent_id even if included in the body."""
    r = client.post("/themes", json={"body_md": "My Theme"})
    theme_id = r.json()["id"]

    r = client.post(
        f"/themes/{theme_id}/breadcrumbs",
        json={"body_md": "Parent"},
    )
    parent_id = r.json()["id"]

    r = client.post(
        f"/themes/{theme_id}/breadcrumbs",
        json={"body_md": "Child", "parent_id": parent_id},
    )
    child_id = r.json()["id"]

    # Try to unset parent_id via update — should be ignored
    r = client.put(
        f"/themes/{theme_id}/breadcrumbs/{child_id}",
        json={"body_md": "Updated child"},
    )
    assert r.status_code == 200
    assert r.json()["parent_id"] == parent_id


def test_delete_theme_cascades_nested_breadcrumbs(client):
    """Deleting a theme removes all breadcrumbs including nested children."""
    r = client.post("/themes", json={"body_md": "Doomed Theme"})
    theme_id = r.json()["id"]

    # Create parent breadcrumb
    r = client.post(
        f"/themes/{theme_id}/breadcrumbs",
        json={"body_md": "Parent"},
    )
    parent_id = r.json()["id"]

    # Create child breadcrumb
    client.post(
        f"/themes/{theme_id}/breadcrumbs",
        json={"body_md": "Child", "parent_id": parent_id},
    )

    # Delete the theme
    r = client.delete(f"/themes/{theme_id}")
    assert r.status_code == 204

    # Theme and all breadcrumbs should be gone
    r = client.get(f"/themes/{theme_id}")
    assert r.status_code == 404
