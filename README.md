# lmgw-dev.github.io

The project site of [lmgw](https://github.com/lmgw-dev/lmgw) and the apps built on it, served at
<https://lmgw-dev.github.io/>. A static site built with [Zola](https://www.getzola.org/), with no
JavaScript, no tracking and no third-party requests: fonts and images are served from here.

## Working on it

```sh
just serve      # live preview on http://127.0.0.1:1111 (fetches the pinned Zola into .tools/ first)
just build      # build into public/, as the Pages workflow does
just check      # build and check every link, external ones included
just shots      # screenshots of every page, light, dark and phone width, into target/shots/
```

`just shots` needs `just serve` running, Google Chrome and `python3-websockets`.

## Layout

| Path | What |
| --- | --- |
| `content/` | The pages, in Markdown. Content is templated, so components work in it: `{{ <shot … /> }}`, `{% <gallery> %}`. |
| `templates/` | `base.html` (header, footer), one template per page kind, `components.html` (the components, and the API reference's schema rendering). |
| `static/css/site.css` | All styles. The palette follows the lmgw dashboard's (`crates/lmgw-ui/assets/app.css`), dark first, light from the OS setting. |
| `static/img/shots/` | Dashboard screenshots, from lmgw's `docs/screenshots/`. The build makes WebP copies for the page and links the PNGs. |
| `static/openapi-v1.json` | lmgw's inference-plane OpenAPI document; `templates/api.html` renders the API reference from it. |
| `data/releases.json` | The lmgw releases from GitHub, trimmed by `scripts/releases.jq`. |
| `tools.env` | The Zola version and its SHA-256, used by `just` and by the workflow alike. |

## Data from lmgw

- **The API reference** comes from the gateway's own OpenAPI document. After an lmgw release,
  check out its tag in the lmgw repository and run `just openapi` (it runs lmgw-core's `openapi`
  example, which prints what `GET /v1/openapi.json` serves; `LMGW_DIR` points at the checkout,
  default `../lmgw`). Commit the new `static/openapi-v1.json`.
- **The release list** is fetched on every Pages build, which also runs daily, so a new release
  shows up within a day without a commit. `just releases` refreshes the committed copy, which the
  build falls back to.
- **Screenshots** are copies of lmgw's `docs/screenshots/`; refresh them when those change.

## Deploying

`.github/workflows/pages.yml` builds and deploys on every push to `main`, daily, and by hand. The
repository's Pages source must be set to **GitHub Actions** (Settings → Pages).

## License

The site (text, templates, styles and scripts) is under the MIT License ([LICENSE](LICENSE)). Two
parts keep their own terms: IBM Plex in `static/fonts/` is under the SIL Open Font License 1.1
(`static/fonts/OFL.txt`), and the logo and screenshots are lmgw's, from its repository
([FSL-1.1-MIT](https://github.com/lmgw-dev/lmgw/blob/main/LICENSE.md)).
