aix code licenses [--gate] [--report]        (also: aix code licences)

THE LICENCE OF EVERY INSTALLED DEPENDENCY, from the package metadata on disk, never the network:
  python   the dist-info of every package under the project's .venv/ or venv/ (License-Expression, the License
           classifier, or the License field)
  npm      every package.json inside node_modules/ (scoped packages included, transitive ones as installed)
  cargo    every package of Cargo.lock whose source sits in the Cargo registry cache (~/.cargo/registry/src)
  maven    every pom.xml dependency present in the local repository (~/.m2/repository)
A package a manifest names that no metadata covers is listed as NOT INSTALLED: install, then re-run.

The classes
  permissive        MIT, BSD, Apache-2.0, ISC, 0BSD, Unlicense, Zlib, PSF, CC0, BlueOak, Boost, WTFPL, MPL-1
  weak copyleft     LGPL, MPL-2.0, EPL, CDDL, CPL, OSL, CC-BY: fine as an unmodified library; keep the notice
  strong copyleft   GPL, AGPL, SSPL, EUPL, CC-BY-SA, BUSL: allowed only when the product's licence is compatible
  proprietary       UNLICENSED / PROPRIETARY / COMMERCIAL: check the terms you agreed to
  unknown           nothing, "UNKNOWN", "SEE LICENSE IN ...": read the package's LICENSE file and record it
  `A OR B` takes the most permissive of the two, `A AND B` the most restrictive.

Deciding, in .aix/config.yaml
  licenses_allow: [GPL-3.0-only]     licence ids accepted whatever their class (the ADR that says why is yours)
  licenses_known:                    what you read in a LICENSE file the metadata did not state
    some-package: MIT

  --gate       exit 1 while any strong copyleft, proprietary or unknown licence is undecided (NOT INSTALLED does not fail it)
  --report     also write docs/tests/code-licenses.md

What this is not: legal advice; a scan of what the code links to at runtime; a check of vendored or copied code.
The skill security-audit-licenses runs it, reads the LICENSE files behind the unknowns, and records the decisions.
