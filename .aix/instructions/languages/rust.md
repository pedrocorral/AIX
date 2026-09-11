---
id: aix/languages/rust
name: "Rust Conventions"
description: "Use when writing or changing Rust: edition and MSRV, toolchain (rustfmt, clippy, cargo test), error handling, unsafe, dependencies. Decisions, not a tutorial."
applyTo: "**/*.rs,**/Cargo.toml"
optional: true
---
# Rust conventions

Decisions this codebase has made. Replace this file in your organisation layer to state yours.

## Edition and toolchain
- Edition 2024 (or the one in `Cargo.toml`); `rust-version` (MSRV) declared and checked in CI; `rust-toolchain.toml` committed when a specific channel is required.
- `cargo fmt --check` and `cargo clippy --all-targets --all-features -D warnings` must pass; `cargo test` for unit and integration tests; `cargo doc` without warnings for public crates.
- `Cargo.lock` committed for binaries; dependencies audited (`cargo deny` or `cargo audit`) in CI; features additive only.

## Errors
- Libraries: a crate-level `Error` enum with `thiserror`; binaries: `anyhow` (or `eyre`) at the top level only.
- No `unwrap` or `expect` outside tests and `main` (`clippy::unwrap_used` denied); `expect` carries a message saying why it cannot fail.
- `?` everywhere; convert at the boundary with `From` impls, not with `map_err` chains repeated per call site.
- `panic!` only for programming errors that cannot be represented; never for input validation.

## Unsafe and concurrency
- `#![forbid(unsafe_code)]` in every crate that does not need it; each `unsafe` block has a `// SAFETY:` comment stating the invariant.
- Prefer ownership and borrowing over `Rc<RefCell<_>>`; `Arc<Mutex<_>>` only across threads and never held across an `.await`.
- Async runtime chosen once per binary (`tokio`); no blocking calls in async code (`spawn_blocking`).

## Structure
- Modules under 400 lines, functions under 60 (`aix code style`); one public type or trait per file is the default.
- Public API documented (`#![warn(missing_docs)]` for libraries); `pub(crate)` by default, `pub` only when a consumer exists.
- Newtypes for domain values (`UserId(u64)`), enums for closed sets, builders for structs with more than 5 optional fields.
