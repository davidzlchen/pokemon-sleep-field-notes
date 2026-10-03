# Import your own full snapshot

A supported private JSON response contains `UD.pokemon.all` (a dictionary keyed
by each record's `pid`), `UD.invent.all`, and optionally `UD.main.all.coin`.
Use one full response for both Pokémon and inventory. A partial update, empty box,
invalid date, or mismatched IDs is rejected. Missing Dream Shards remain unknown.

1. Store your raw response outside the public website and repository, or under
   ignored `.private/`. It can contain credentials and account data.
2. Configure your public name and timezone as described in the README. Calendar
   dates use that timezone; full raw capture timestamps are not published.
3. On the first import only, run `python3 scripts/remove_demo.py`. This checks the
   exact fictional demo files and refuses to remove a changed/real collection.
4. Run `scripts/sync_sleep_collection.py --source /private/path/full-response.json
   --captured-at YYYY-MM-DD`. Use the date the data was actually captured.
5. Run the README checks. Inspect the public roster/inventory for any text you do
   not want shared, including nicknames and game island/date met. Allowlisting
   removes unexpected fields, not personal words you chose as nicknames.
6. Compare the count and a few helpers' ingredient/subskill/XP details against
   the app. Species game IDs differ from National Pokédex numbers. Unknown IDs
   remain unresolved; don't invent a match to make a demo look complete.

## Preview without serving private files

After capture/import, do not serve the repository root. Stage only public files:

```sh
python3 scripts/stage_site.py --output /tmp/my-sleep-public
python3 -m http.server 8765 --directory /tmp/my-sleep-public
```

Open http://localhost:8765/pokemon-sleep/. Refresh the staged files after later
imports. The staging command rejects an existing nonempty output directory.
Snapshots are paired and named by capture date plus a content hash. Reimporting
the same data is idempotent; a different capture on the same date is kept.

The website uses snapshot-local `mon-N` identifiers. They do not track a Pokémon
across captures; shared links pin the snapshot as well as the row ID.

## Refresh

Supply another complete snapshot and repeat the import/verification/deployment.
No background account access is installed. Publish the whole static output in
one deployment. The original private login-refresh helper is deliberately absent.
