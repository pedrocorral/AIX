---
id: META-STACK-JAVA
title: Spring Boot mapping
---
# Spring Boot mapping
- Layout: `backend/src/main/java/<pkg>/<domain>/{controller,dto,service,model,repository,adapter/{jpa,memory}}` — same roles as `../../architecture/project-layout.md`; tests mirror under `src/test/java`.
- Controllers: `@RestController` thin; DTOs are records; validation with Jakarta annotations at the boundary.
- Domain models are plain classes; JPA entities live in `adapter/jpa` with explicit mappers (avoid annotating domain classes).
- Ports are interfaces in `repository`; Spring Data repositories are *implementation details* wrapped by the adapter, not exposed to services.
- Unit of work = `@Transactional` on service methods; repositories never manage transactions.
- Composition = Spring configuration classes selecting adapters by `@ConditionalOnProperty("persistence.backend")`.
- Tests: JUnit 5, AssertJ, Testcontainers, ArchUnit for the dependency rule, Spring Boot slice tests for controllers.
- Security: Spring Security; method-level authorisation in services (`@PreAuthorize` or explicit policy), OWASP dependency-check.
