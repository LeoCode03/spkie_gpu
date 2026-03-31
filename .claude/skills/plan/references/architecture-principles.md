# Architecture Principles

## The central rule

The domain is the centre. It knows nothing about HTTP, databases, queues, or any framework. All external interaction flows through ports/interfaces and adapters/implementations.

This is not a preference. It is the invariant the entire system is built on. A violation of this rule is not a code quality issue — it is an architectural failure.

---

## Layer structure

```
┌─────────────────────────────────────────────────────────┐
│                     INBOUND ADAPTERS                     │
│   Routers · Controllers · Event consumers · CLI · Jobs   │
├─────────────────────────────────────────────────────────┤
│                   APPLICATION LAYER                      │
│          Commands (writes) · Queries (reads)             │
├─────────────────────────────────────────────────────────┤
│                     DOMAIN LAYER                         │
│     Models · Ports · Services · Events · Exceptions      │
├─────────────────────────────────────────────────────────┤
│                    OUTBOUND ADAPTERS                     │
│   Repositories · API clients · Gateways · Publishers     │
└─────────────────────────────────────────────────────────┘
```

This is the hexagonal/clean architecture view. Simpler projects may use a layered structure (controller → service → repository) — the dependency direction rule still applies: inner layers never import outer layers.

---

## Dependency direction — strict

Inner layers must never depend on outer layers.

**Hexagonal / Clean Architecture:**
```
domain/      → NOTHING (stdlib and typing only)
application/ → domain/ ONLY
adapters/    → domain/ + application/ + external libraries
config/      → everything (composition root)
```

**Layered (MVC / service-repository):**
```
models/      → NOTHING
services/    → models/ ONLY
controllers/ → services/ + models/
config/      → everything
```

The exact directory names vary by stack — read the project's `ARCHITECTURE.md` or stack reference for the actual paths. The rule is the direction, not the names.

---

## Directory structure

The exact layout depends on the language and framework. Common patterns:

**Hexagonal (Python, TypeScript, Go, Kotlin):**
```
src/
├── domain/          # Models, ports/interfaces, services, events, exceptions
├── application/     # Commands, queries, use cases, DTOs
├── adapters/
│   ├── inbound/     # Routers, controllers, event handlers
│   └── outbound/    # Repositories, API clients, gateways
└── config/          # DI container, settings, wiring
```

**Layered MVC (Rails, Django, Laravel, Spring):**
```
app/
├── models/          # Domain models, validations
├── services/        # Business logic
├── controllers/     # HTTP handlers
└── config/          # Settings, routes
```

**Feature-based (Next.js, Flutter, React):**
```
src/ or lib/
├── features/
│   └── <feature>/
│       ├── domain/      # Models, interfaces
│       ├── data/        # Repositories, API calls
│       └── presentation/ # UI, controllers, pages
└── core/                # Shared utilities, base classes
```

Use whatever structure the project already has. The principle is dependency direction, not directory names.

---

## What belongs in each layer

### Inner layer (domain / models)

- Entities, value objects, aggregates
- Port interfaces or abstract classes — no implementations
- Domain services that orchestrate entities and ports
- Domain events (immutable data objects)
- Domain exceptions that describe business failures (not HTTP status codes)

Inner-layer code may not import framework types, database drivers, HTTP libraries, cloud SDKs, or any infrastructure dependency.

### Middle layer (application / services / use cases)

- Command handlers: one per write operation
- Query handlers: one per read operation
- DTOs used by commands and queries

May import from inner layer only. May not import adapter code.

### Outer layer (adapters / controllers / infrastructure)

- HTTP handlers, routers, controllers
- Event consumers and publishers
- Repository implementations (translate between domain models and persistence)
- External API adapters (translate between domain ports and external APIs)
- Gateway wrappers (add retry, circuit breaking, rate limiting)
- Request/response schemas and serialization

### Composition root (config / wiring)

- Dependency injection container or wiring module
- Settings and environment configuration
- Event bus wiring
- May import from all layers — this is the only place where the full dependency graph is visible

---

## CQRS separation (when applicable)

If the project uses CQRS:
- Every write operation is a Command with a CommandHandler
- Every read operation is a Query with a QueryHandler
- Commands and queries are never mixed in the same handler
- A command handler must not return query results

Not all projects use CQRS. Simpler projects may have a single service layer handling both reads and writes — this is fine if the project is structured that way.

---

## What these principles protect

1. The domain can be unit-tested without any infrastructure
2. Any adapter can be replaced without touching domain or application code
3. The system can be reasoned about layer by layer
4. Data isolation can be enforced at a single boundary
