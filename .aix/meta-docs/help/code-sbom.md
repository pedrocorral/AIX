aix code sbom [--spdx] [--out FILE] [--gate] [--report] [--selftest]      aix blackduck  =  aix code sbom --gate

THE BILL OF MATERIALS AND THE COMPOSITION POLICY: what a Black Duck scan gives, from the kit's own tools.
One command answers the three questions software composition analysis asks: what does the product install, under
which licences, with which known vulnerabilities; and one verdict says whether it may ship.

What goes in the bill
  components     every package the project installs: lockfiles as they are (uv/poetry/pdm/Cargo.lock, package-lock,
                 pnpm-lock, yarn.lock, Pipfile.lock, Gemfile.lock, composer.lock, go.sum), `==` pins and pom.xml
                 dependencies with everything they pull in (resolved through deps.dev), the same inventory as
                 aix code vulnerabilities --cve; each with its purl and the manifest it comes from
  licences       from the metadata installed on disk, the same reading as aix code licenses (dist-info under the
                 venv, node_modules, the Cargo and Maven caches), classed permissive / weak copyleft / strong
                 copyleft / proprietary / unknown; `licenses_known:` and `licenses_allow:` apply. Nothing installed
                 -> no licence column, and the licence half of the policy does not run (it says so)
  advisories     every OSV advisory of every component, with a severity: the CVSS 3.x base score computed from the
                 advisory's vector (the specification's arithmetic, --selftest proves it on published scores), else
                 the label its database gives, else unknown; and the first fixed version for that package

Formats
  CycloneDX 1.5 JSON (default), docs/security/sbom.cdx.json: components with purl, licence and manifest,
                 vulnerabilities with source, rating, affected components and the recommended upgrade
  --spdx         SPDX 2.3 JSON, docs/security/sbom.spdx.json: packages and licences (SPDX carries no advisories;
                 they stay in the printed report)
  --out FILE     elsewhere

The policy (--gate, and `aix blackduck`)
  FAILS on an advisory at or above `sbom_max_severity` (.aix/config.yaml; default high: high and critical fail,
  medium and low are listed), or on a licence to decide (strong copyleft, proprietary, unknown) when licences
  could be read. Decide a licence with `licenses_allow:` / `licenses_known:` (aix help code licenses); an advisory
  with an upgrade, or `aix: accepted VUL-DEP-001 <why>` is not enough here: the bill is for auditors, the
  register keeps the reasoning (VUL-DEP-001 row). The step `sbom` is advised in the release policy.

Network: OSV and deps.dev. Resolved graphs are cached under ~/.cache/aix/depsdev for good, advisories under
~/.cache/aix/osv for a day. Unreachable -> the bill is written with what could be read, marked partial, and the
gate does not fail for that reason.

A bill is an inventory, not a proof: a package present is exposed only where it is used, and an advisory applies
to the version. Related: aix code vulnerabilities --cve (the same advisories as findings), aix code licenses,
skill security-audit-licenses, aix docs security (VUL-DEP-001).
