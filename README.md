# Pokémon Sleep Repository

Turn your own Pokémon Sleep collection into a searchable website with ingredients,
subskills, XP progress, supplies, historical snapshots, and links to individual helpers.
Built to be used with Claude Code or Codex. No frontend framework or build step required.

**Start by giving your agent this prompt:**

> Read https://github.com/davidzlchen/pokemon-sleep-repository and follow its
> AGENTS.md. Create my own Pokémon Sleep repository using this template. Show me
> the local demo first, then help me import my own data. Keep all captures,
> credentials, and raw account responses private. Ask for my public display name
> and timezone. Verify the collection before helping me publish it.

The agent can clone the template, configure it, import a snapshot, validate the
exports, and show the website. **It cannot obtain your account data from a prompt
alone.** You must supply your own decoded full snapshot, or complete the optional
phone capture steps. The capture path is experimental and tied to one exact
v3.8.2 client revision; it is not an official Pokémon Sleep export API.

## Try it in one minute

Requires Python 3.11+; Node.js is needed only for the JavaScript checks.

```sh
git clone https://github.com/davidzlchen/pokemon-sleep-repository.git
cd pokemon-sleep-repository
python3 -m http.server 8765
```

Open http://localhost:8765/pokemon-sleep/. The included helper is **fictional demo
data dated January 1, 2000**, not David's collection. No account access is needed.

## Make it yours

```sh
python3 scripts/configure.py --name "Your public name" --timezone "America/New_York"
```

Use [the import guide](docs/import.md) for an existing full decoded snapshot, or
[the capture guide](docs/capture.md) to obtain one from your own phone session.
Both paths end with the same offline, validated import:

```sh
python3 scripts/sync_sleep_collection.py \
  --source /absolute/private/path/full-response.json \
  --captured-at YYYY-MM-DD
```

Use the **actual capture date**. For your first import, remove the fictional demo
using `python3 scripts/remove_demo.py`. That command refuses to remove real data.
Never substitute incremental `UD.pokemon.upd` records for a complete
`UD.pokemon.all` response. The importer validates the paired roster and inventory
in isolation before replacing published files. An invalid import keeps the last
published collection. Deploy the complete output together so readers see one version.

## Verify and publish

```sh
python3 -m unittest discover -s scripts -p 'test_*sleep*.py'
python3 -m unittest discover -s scripts -p test_map_api_roster.py
node scripts/test_sleep_search.cjs
node scripts/test_sleep_assets.cjs
```

Only publish the static site: `index.html` and `pokemon-sleep/`. Vercel's included
ignore file excludes scripts, docs, and private working files from deployment.
Any host supporting root-relative static paths works; GitHub Pages needs a custom
root domain or paths adapted for a project subdirectory. Create a repository you
own and review `git diff --cached` before publishing. See [agent instructions](AGENTS.md).

## What is reusable

- A static collection browser with search, specialty/shiny filters, sorting,
  helper details, supplies, and snapshot-pinned share links.
- Offline mapping from game IDs to English names, species-specific XP curves,
  unlock levels, main-skill bonuses/caps, minted natures, and special Mythical slots.
- Explicit allowlist exports: no raw responses, session values, account IDs,
  Pokémon instance IDs, diamonds, or purchase fields in the public output.
- Immutable paired roster/inventory snapshots and tests using synthetic inputs.
- Optional offline capture decoder and a single-request full-data fetcher.

Unknown mappings remain unavailable/reviewable. Some skill defaults come from
community species references and are marked accordingly. Reference data is a
snapshot of master version 134, not a guarantee of compatibility with future updates.

## What is not included

No original player data, captures, tokens, certificates, native game binaries,
account login refresh, scheduled requests, or hosted credential-bearing service.
The original site's weekly sync uses its owner's separate private session runtime;
that setup is **not** bundled or claimed as ready for other accounts.

## Credits

[Original collection](https://davidzlchen.com/pokemon-sleep/) ·
[Build story](https://davidzlchen.com/blog/pokemon-sleep-repository/) ·
[PokéAPI sprites](https://github.com/PokeAPI/sprites) ·
[Neroli's Lab](https://github.com/nerolis-lab/nerolis-lab) ·
[RaenonX](https://pks.raenonx.cc/en/item/overview).

See [NOTICE](NOTICE) for third-party game data and artwork. This is an independent
fan project and is not affiliated with Pokémon, Nintendo, or SELECT BUTTON.
