# Testing Quality Rules

## Purpose

Tests are the enforcement mechanism for acceptance criteria. These rules define what makes a test suite adequate — not just present.

---

## Test structure

```
tests/
├── conftest.py                           # Shared fixtures
├── unit/
│   ├── domain/
│   │   ├── test_<feature>_models.py     # Entity/VO validation, business rules, state machines
│   │   └── test_<feature>_services.py   # Domain service logic (mocked ports)
│   └── application/
│       ├── test_<feature>_commands.py   # Use case tests (mocked ports)
│       └── test_<feature>_queries.py    # Query tests (mocked ports)
├── integration/
│   └── test_<feature>_adapters.py       # Adapter tests (real DB, fake externals)
└── e2e/
    └── test_<feature>_api.py            # Full API tests (FastAPI TestClient)
```

---

## Coverage requirements

### Mandatory for every CR that touches acceptance criteria

- One test skeleton per acceptance criterion
- One happy-path test per operation
- One error-path test per error scenario in the spec

### Mandatory for every CR that touches data access

- One cross-tenant isolation test per data access path — **non-negotiable**
- A test that verifies Tenant B cannot read, write, or enumerate Tenant A's data through the code path under test

### Mandatory for every CR that adds or modifies auth

- Unauthenticated request returns 401
- Insufficient role returns 403
- Cross-tenant request returns 404 (not 403 — do not reveal existence)

---

## Test naming convention

```python
def test_<action>_<condition>_<expected_result>():
    """Maps to AC-N: GIVEN <precondition> WHEN <action> THEN <outcome>"""
```

Every test must document which AC or error scenario it covers in its docstring.

---

## Fixture rules

- Tests use fake repositories (in-memory implementations), not mocked internals
- Tests do not mock domain objects — they construct them
- Shared fixtures live in `conftest.py`: `tenant_uid`, `other_tenant_uid`, fake repos, fake event bus
- Fixtures must produce isolated state — no shared mutable state between tests

```python
@pytest.fixture
def tenant_uid() -> str:
    return "tenant-test-001"

@pytest.fixture
def other_tenant_uid() -> str:
    return "tenant-test-002"
```

---

## Test skeleton design rules

Test skeletons are designed to fail until the implementation exists. A skeleton that passes before implementation is not a valid skeleton.

Every skeleton must have:

```python
async def test_<name>(self):
    """AC-N: <criterion text>"""
    # GIVEN
    # WHEN
    # THEN
    raise NotImplementedError
```

The `raise NotImplementedError` is removed when the test is implemented during Build.

---

## Tenant isolation test pattern

```python
class TestTenantIsolation:
    async def test_cannot_access_other_tenant_resource(self, handler, other_tenant_uid):
        # GIVEN data created for tenant A
        await handler.execute(Command(tenant_uid="tenant-a", ...))
        # WHEN tenant B queries for tenant A's resource
        # THEN it raises EntityNotFound (not returns data, not raises AuthError)
        with pytest.raises(EntityNotFound):
            await query_handler.execute(Query(tenant_uid="tenant-b", entity_id=...))

    async def test_list_returns_only_own_tenant_data(self, handler):
        # GIVEN data for two different tenants
        await handler.execute(Command(tenant_uid="tenant-a", ...))
        await handler.execute(Command(tenant_uid="tenant-b", ...))
        # WHEN tenant A lists their data
        results = await query_handler.execute(ListQuery(tenant_uid="tenant-a"))
        # THEN only tenant A's data is returned
        assert all(r.tenant_uid == "tenant-a" for r in results.items)
```

---

## What makes a test inadequate (finding triggers)

| Condition | Severity |
|---|---|
| Acceptance criterion with no corresponding test | HIGH |
| Data access path with no cross-tenant isolation test | HIGH |
| Test that passes before implementation exists | HIGH |
| Error scenario from the spec with no corresponding test | MEDIUM |
| Test that does not follow GIVEN/WHEN/THEN structure | LOW |
| Missing auth failure test for an authenticated endpoint | MEDIUM |
| Test with shared mutable state between test cases | MEDIUM |

---

## Adversarial checklist

For every feature, verify these edge cases are considered:

- [ ] Rate limit triggers and returns 429
- [ ] Concurrent writes don't corrupt state (optimistic lock test if applicable)
- [ ] Idempotent operation with duplicate key returns original response, no duplicate side effect
- [ ] Invalid UUID or ID in path parameter returns 400
- [ ] Expired JWT returns 401
- [ ] Member role cannot perform admin-only actions
- [ ] Member cannot read admin-only fields in the response body
- [ ] Empty list returns empty array, not 404 or null
