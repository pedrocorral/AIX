# policies/ — development cycles a project can opt into (`aix policy`)

One file per policy: `order` (the steps), `required` and `advised` (their level), optional `checks` (extra steps of your own: id -> command). Steps are the ones `aix help policy` lists. `anarchy` is the default and has no file: nothing checked. A layer (`org/`, `custom/`) adds or replaces a policy by placing the same file under its `policies/`, and sets its default with `defaults.yaml` (`policy: standard`).
