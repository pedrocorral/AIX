---
id: aix/languages/java
name: "Java Conventions"
description: "Use when writing or changing Java: version floor, build and quality tools (Maven or Gradle, Spotless, Error Prone, JUnit 5), errors, logging, dependencies. Decisions, not a tutorial."
applyTo: "**/*.java,**/pom.xml,**/build.gradle,**/build.gradle.kts"
optional: true
---
# Java conventions

Decisions this codebase has made. Replace this file in your organisation layer to state yours.

## Version and features
- Floor: the `release` / `sourceCompatibility` in the build file; LTS only (17, 21, 25). `aix code style --modernise` reports code older than the floor.
- Use what the floor allows: records for data, sealed interfaces for closed hierarchies, `switch` expressions with pattern matching, text blocks, `var` for obvious locals only, virtual threads (21+) for blocking I/O instead of thread pools.
- No `Optional` fields or parameters; `Optional` only as a return type for absence.

## Toolchain (must pass before "done")
- One build tool (Maven or Gradle) with the wrapper committed; dependency versions pinned in one place (BOM or version catalog).
- `Spotless` with `google-java-format` (or `palantir`) for formatting; `Error Prone` and `NullAway` (or `-Xlint:all -Werror`) for bugs; Checkstyle only for what those do not cover.
- `JUnit 5` + `AssertJ`; `Mockito` only at boundaries; `Testcontainers` for anything that talks to a real service; `JaCoCo` threshold in the build.
- No `System.out`; SLF4J with a per-class logger; no secrets or PII in messages.

## Errors
- Unchecked exceptions from the project's `errors` package; checked exceptions only when the caller can recover; never swallow (`catch (Exception e) {}`) and never `catch (Throwable)`.
- Fail fast on invalid arguments (`Objects.requireNonNull`, guard clauses); validate external input at the boundary (Bean Validation on DTOs).

## Structure
- Package by domain, not by layer (`com.acme.orders`, not `com.acme.controllers`); `aix code graph --gate` enforces the direction between domains.
- Classes under 400 lines, methods under 60, at most 5 parameters (`aix code style`); constructor injection only, no field injection.
- Immutable by default: `final` fields, records for values, unmodifiable collections returned.
