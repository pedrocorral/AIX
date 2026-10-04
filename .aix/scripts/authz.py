"""VUL-AUTHZ-001 (CWE-639): a Java web handler that takes an id from the URL, loads or changes a user-owned thing
by that id, and never ties it to the caller. Three questions per handler: does the project have logins at all (a
security dependency or configuration), does the loaded entity have an owner (a user-typed field or an owner id),
is the caller compared with the owner anywhere on the way (a security annotation, a principal read, an owner-aware
repository method, an owner comparison), in the handler or in the method it calls one level down.
Not a finding: a project without authentication, an entity without an owner, an admin-only handler."""
import re
from pathlib import Path

from codefiles import ROOT, rel, source_files
from javataint import METHOD, _load

ROW = "VUL-AUTHZ-001"
SNIPPET = 110
RULE = (ROW, "CWE-639", "{id} handler reaches a user-owned {entity}{via} with no ownership check",
        "load it through the caller (findByIdAndUser(id, currentUser)) or compare its owner with the principal before returning or changing it")
SECURITY_DEP = re.compile(r"spring-security|spring-boot-starter-security|spring-boot-starter-oauth2|keycloak|shiro-|jakarta\.security|pac4j")
SECURITY_CODE = re.compile(r"@EnableWebSecurity|SecurityFilterChain|WebSecurityConfigurerAdapter|@EnableMethodSecurity|@EnableGlobalMethodSecurity|HttpSecurity\b")
ENTITY = re.compile(r"\bclass\s+(\w+)")   # any class: an owned thing may be an @Entity or a plain object built from the id
FIELD = re.compile(r"^[ \t]*(?:@\w+(?:\([^)]*\))?[ \t]*)*(?:private|protected|public)?[ \t]*(?:final[ \t]+)?(?P<type>[\w.]+)(?P<generic><[^>]*>)?[ \t]+(?P<name>\w+)[ \t]*[;=]", re.M)
OWNER_TYPES = {"User", "Users", "AppUser", "UserEntity", "UserAccount", "Owner", "Principal", "Tenant", "Member", "Customer"}
OWNER_NAMES = re.compile(r"^(?:user|owner|tenant|userId|ownerId|tenantId|userLogin|customer|member)$")   # not createdBy/login: audit and identity fields, not ownership
MAPPING = re.compile(r"@(?:Get|Post|Put|Delete|Patch|Request)Mapping\b|@(?:GET|POST|PUT|DELETE|PATCH)\b")
PATH_PARAM = re.compile(r"@(?:PathVariable|PathParam)\b")
ANNOTATED = re.compile(r"@(?:PreAuthorize|PostAuthorize|Secured|RolesAllowed|PermitAll|DenyAll|PreFilter|PostFilter)\b")
CHECK = re.compile(r"getCurrentUser\w*|getAuthentication\(|getPrincipal\(|getUserPrincipal|SecurityContextHolder|@AuthenticationPrincipal|\bPrincipal\s+\w+|\bAuthentication\s+\w+"
                   r"|isCurrentUser|hasRole|hasAuthority|hasPermission|checkAccess|assertOwner|verifyOwner|canAccess|isOwner|ownedBy"
                   r"|And\w*(?:User|Owner|Login|CreatedBy|Tenant|Customer|Member)\w*\(|IsCurrentUser|By\w*(?:User|Owner|Tenant|Customer|Member)\w*\(|ForCurrentUser"
                   r"|\.get(?:User|Owner|CreatedBy|Login|Tenant|Customer|Member)\(\)")
REPO_CALL = re.compile(r"\b(\w+?)(?:Repository|Repo|Dao|DAO|Mapper)\s*\.\s*\w+\s*\(")
SERVICE_CALL = re.compile(r"\b\w+(?:Service|Manager|Facade)\s*\.\s*(\w+)\s*\(((?:[^()]|\([^()]*\))*)\)")
GENERIC_RETURN = re.compile(r"(?:ResponseEntity|Optional|List|Set|Page|Mono|Flux)<\s*(\w+)\s*>")
CLASS = re.compile(r"((?:@\w+(?:\([^)]*\))?\s*)*)\s*(?:public\s+)?(?:final\s+)?class\s+(\w+)")


def _java_files(paths) -> dict:
    out = {}
    for p in paths:
        base = (ROOT / p) if not Path(p).is_absolute() else Path(p)
        for f in ([base] if base.is_file() else source_files([str(base)])):
            if f.suffix == ".java" and _load(f) is not None:
                out[f] = _load(f)[0]
    return out


def authenticated(paths, files: dict) -> bool:
    """Logins exist: a security dependency in a build file under the project, or security configuration in the code."""
    for name in ("pom.xml", "build.gradle", "build.gradle.kts", "gradle/libs.versions.toml", "settings.gradle"):
        for build in [ROOT / name] + [((ROOT / p) if not Path(p).is_absolute() else Path(p)) / name for p in paths]:
            if build.is_file() and SECURITY_DEP.search(build.read_text(encoding="utf-8", errors="replace")):
                return True
    return any(SECURITY_CODE.search(text) for text in files.values())


def _class_fields(files: dict) -> dict:
    """class name -> [(field type, field name, is a collection)] for every class."""
    out = {}
    for text in files.values():
        m = ENTITY.search(text)
        if m:
            out[m.group(1)] = [(f.group("type").split(".")[-1], f.group("name"), bool(f.group("generic"))) for f in FIELD.finditer(text)]
    return out


def owned_entities(files: dict) -> dict:
    """class name -> None when nothing owns it, "" when a field names or types its owner (`private User user`,
    `private String userId`), or the name of the single-valued field through which it is owned one hop away
    (an `Operation` with `private BankAccount bankAccount`). Collections never carry ownership."""
    fields = _class_fields(files)
    direct = {name: any(t in OWNER_TYPES or OWNER_NAMES.match(n) for t, n, _ in fs) for name, fs in fields.items()}
    out = {}
    for name, fs in fields.items():
        via = next((n for t, n, collection in fs if not collection and direct.get(t) and t != name), None)
        out[name] = "" if direct[name] else via
    return out


def _method_bodies(files: dict) -> dict:
    """name -> [(params, body text)] over every file, for the one-level walk into a service."""
    index = {}
    for text in files.values():
        for m in METHOD.finditer(text):
            index.setdefault(m.group(1), []).append((m.group(2), _body(text, m.end() - 1)))
    return index


def _body(text: str, brace: int) -> str:
    depth = 0
    for j in range(brace, len(text)):
        depth += (text[j] == "{") - (text[j] == "}")
        if depth == 0:
            return text[brace:j + 1]
    return text[brace:]


def _handlers(text: str):
    """(line, head, body, class annotations) of every method with a mapping annotation and a path parameter."""
    cls = CLASS.search(text)
    class_annotations = cls.group(1) if cls else ""
    for m in METHOD.finditer(text):
        annotations = _annotations_above(text, m.start()) + text[m.start():m.end()]
        if MAPPING.search(annotations) and PATH_PARAM.search(m.group(2)):
            yield text.count("\n", 0, m.end()) + 1, annotations, _body(text, m.end() - 1), class_annotations


def _annotations_above(text: str, pos: int) -> str:
    """The annotation and comment lines directly above a method head (`@GetMapping("/{id}")` holds a brace, so no
    brace-based cut)."""
    kept, depth = [], 0
    for line in reversed(text[:pos].splitlines()):
        depth += line.count(")") - line.count("(")
        inside = depth > 0   # a continuation line of a multi-line annotation (`produces = {"application/json"})`)
        if line.strip() and not inside and not line.lstrip().startswith(("@", "*", "/*", "//")):
            break
        kept.append(line)
    return "\n".join(reversed(kept))


def _reached(body: str, index: dict) -> str:
    """The body plus the bodies of the service methods it calls, one level down."""
    extra = []
    for m in SERVICE_CALL.finditer(body):
        arity = len([a for a in m.group(2).split(",") if a.strip()])
        extra += [b for params, b in index.get(m.group(1), []) if len([p for p in params.split(",") if p.strip()]) == arity]
    return body + "\n" + "\n".join(extra)


CONSTRUCTED = re.compile(r"\bnew\s+(\w+)\s*\(\s*\w+\s*\)")                      # `new UserProfile(userId)`: built from the id
TYPED_LOAD = re.compile(r"\b([A-Z]\w+)\s+\w+\s*=\s*[\w.]+\.(?:get|find|load|fetch|read)\w*\(")   # `Order o = orders.get(id)`


def _entities_reached(head: str, reached: str) -> list:
    """The classes the handler loads, builds or returns: repository calls, `new X(id)`, typed loads, the return type."""
    names = [m.group(1) for m in REPO_CALL.finditer(reached)] + [m.group(1) for m in CONSTRUCTED.finditer(reached)]
    names += [m.group(1) for m in TYPED_LOAD.finditer(reached)] + [m.group(1) for m in GENERIC_RETURN.finditer(head)]
    return [n[:1].upper() + n[1:] for n in names]


def _file_findings(f: Path, text: str, index: dict, owned: dict) -> list:
    out = []
    for line, head, body, class_annotations in _handlers(text):
        if ANNOTATED.search(head) or ANNOTATED.search(class_annotations):
            continue
        reached = _reached(body, index)
        entities = [e for e in _entities_reached(head, reached) if owned.get(e) is not None]
        if entities and not CHECK.search(head + reached):
            out.append(_finding(f, line, head, entities[0], owned[entities[0]]))
    return out


def _finding(f: Path, line: int, head: str, entity: str, via: str) -> tuple:
    """The register-shaped finding: the mapping line and the method's name line as the snippet."""
    name_line = next((l.strip() for l in head.splitlines() if re.search(r"\b\w+\s*\(", l) and not l.lstrip().startswith(("@", "*", "/"))), "")
    mapping = next((l.strip() for l in head.splitlines() if MAPPING.search(l)), "")
    vul, cwe, title, advice = RULE
    title = title.format(id="{id}", entity=entity, via=f" (owned through its {via})" if via else "")
    return (vul, cwe, title, rel(f), line, (mapping + "  " + name_line)[:SNIPPET], advice, None)


def findings(paths) -> list:
    """VUL-AUTHZ-001 findings for the Java handlers under `paths`; none when the project has no authentication."""
    files = _java_files(paths)
    if not files or not authenticated(paths, files):
        return []
    owned = owned_entities(files)
    if all(v is None for v in owned.values()):
        return []
    index = _method_bodies(files)
    return [fx for f, text in files.items() if MAPPING.search(text) for fx in _file_findings(f, text, index, owned)]
