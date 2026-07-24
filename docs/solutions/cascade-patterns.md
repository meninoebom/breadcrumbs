# Cascade Delete Patterns (SQLModel + SQLAlchemy)

## Hybrid Approach
Use three together for proper cascade delete behavior:
1. **Database level:** `ondelete="CASCADE"` in `Field()` - enforces at SQL level
2. **ORM awareness:** `cascade="all, delete[-orphan]"` in relationship - tells SQLAlchemy what's happening
3. **Efficiency:** `passive_deletes=True` - uses DB cascade for unloaded collections

## When to use `delete-orphan`
- Existential dependency (child can't exist without parent)
- Example: Breadcrumb -> Theme (breadcrumb without theme is invalid)
- Example: Breadcrumb -> Parent Breadcrumb (self-referential, reply without parent is orphaned)
- Deletes children when removed from collection OR parent deleted

## When to use `save-update, merge` only (many-to-many)
- Independent entities linked by a join table
- Example: Theme <-> Tag (both exist independently)
- DB-level `ondelete="CASCADE"` on the join table FKs handles link row cleanup
- Do NOT use `cascade="all, delete"` -- this deletes the *related entities*, not just the association rows

## Example

```python
# One-to-many with orphan deletion (Theme -> Breadcrumbs)
breadcrumbs: List["Breadcrumb"] = Relationship(
    back_populates="theme",
    sa_relationship_kwargs={
        "cascade": "all, delete-orphan",
        "passive_deletes": True,
    }
)

# Many-to-many (Theme <-> Tags) -- link table cleanup via DB cascade
tags: List["Tag"] = Relationship(
    back_populates="themes",
    link_model=ThemeTag,
    sa_relationship_kwargs={
        "cascade": "save-update, merge",
        "passive_deletes": True,
    }
)
```

## PostgreSQL Table Naming
- Explicitly set `__tablename__` for join tables to follow snake_case convention
- Example: `__tablename__ = "theme_tag"` (not auto-generated "themetag")
- Improves readability in psql and aligns with PostgreSQL conventions
