---
id: META-STACK-JS-NODE
title: Node / TypeScript backend
---
# Node / TypeScript backend
- Same domain folders (`controllers, schemas, services, models, repositories, adapters`); NestJS modules map 1:1 to domains; Express/Fastify use routers as controllers.
- Schemas: zod at the boundary; domain models as classes without decorators; ORM (Prisma/Drizzle/TypeORM) confined to `adapters/`.
- Unit of work: transaction wrapper in adapter; services receive `UnitOfWork` port.
- Testing: Vitest/Jest, supertest for functional, Testcontainers; `dependency-cruiser` for the dependency rule.
- Security: helmet, rate limiting, `npm audit`, input size limits.
