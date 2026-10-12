# Vendored front-end libraries

Served locally so the demo page works offline / behind a proxy and no third-party script runs on it.
Both tarballs come from the npm registry and were verified against the registry's published SHA-1.

| Library | Version | License |
|---|---|---|
| Leaflet (`leaflet/`) | 1.9.4 | BSD-2-Clause |
| Bootstrap CSS (`bootstrap/bootstrap.min.css`) | 5.3.8 | MIT |

To update: download the new tarball, check its checksum against `npm view <pkg> dist.shasum`, and copy
`dist/leaflet.{js,css}` + `dist/images/*`, respectively `dist/css/bootstrap.min.css`.
