# persistence/ — storing data without letting storage leak into the app
Read this when: touching anything that reads/writes data. Skip when: purely UI work.

| Path | What | Read when |
|---|---|---|
| `abstraction-layer.md` | Repository + Unit of Work ports, in-memory adapter, rules that make backends swappable | Designing data access; adding an entity |
| `orm-guidelines.md` | How to use an ORM without coupling: mapping strategies, sessions, lazy loading, N+1, transactions | Writing ORM code |
| `switching-backends.md` | Selecting/replacing a backend (SQL, document, file, memory) via config; contract test suite | Adding or changing a backend |
| `migrations-and-data-lifecycle.md` | Schema migrations, seeding, backups, retention, PII deletion | Schema change; NFR-DATA |
