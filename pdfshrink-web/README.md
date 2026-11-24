# pdfshrink (web)

Client-side PDF compressor. Ghostscript compiled to WebAssembly, so PDFs never leave the browser.

## Deploy on GitHub Pages
1. Create a repo and push everything in this folder to `main`
   (`gs.wasm` is ~16 MB, well under GitHub's 100 MB file limit).
2. Repo → Settings → Pages → Source: "Deploy from a branch" → `main` / `(root)`.
3. Open `https://<user>.github.io/<repo>/` after about a minute.

Test locally first (workers and WASM need http, not file://):

    python3 -m http.server 8000   # then open http://localhost:8000

## Files
- `index.html`: UI and Ghostscript options
- `worker.js`: runs Ghostscript in a Web Worker
- `gs.js`, `gs.wasm`: Ghostscript build from npm `@jspawn/ghostscript-wasm@0.0.2`

## License
Ghostscript is AGPL-3.0, so this repo is AGPL-3.0 (see `LICENSE`). Keep the repo public
(or otherwise make the source available) while the site is live.
