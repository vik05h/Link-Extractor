# Firebase Database Setup

The app reaches the Community Cloud Cache with no login, so these rules are the only thing that protects it. Nothing in the app can do this job, because anyone can send requests to the database directly.

## What the rules do

| Path | Anyone can | Only the admin key can |
| :--- | :--- | :--- |
| `games_meta`, `games_urls` | Read. Add or update a game if its fields are valid and its links are on `dl.fuckingfast.co`. | Delete a game. |
| `reports` | Read. Create a report, add a comment, add a vote. | Change status or remark, post as admin, delete. |
| `report_screenshots` | Read. Add a screenshot image. | Replace or delete a screenshot. |
| `crash_logs` | Add a crash report. | Read, change or delete. |
| Anything else | Nothing. | Everything. |

## Applying the rules

1. Test them first if you can. See "Testing" below.
2. Open the [Firebase console](https://console.firebase.google.com/), select the project, then open **Realtime Database**, **Rules**.
3. Copy the old rules somewhere safe so you can restore them.
4. Paste the contents of `database.rules.json` and click **Publish**.

Changes take effect immediately for every installed copy of the app.

## Admin Mode

Admin Mode in the Issue Center uses the Firebase database secret as its key. The database checks the key on every change, so nothing on a user's PC can grant admin rights.

1. In the Firebase console, open **Project settings**, **Service accounts**, **Database secrets**.
2. Copy the secret.
3. In the app, open the Issue Center, click the lock, and paste it.

The app keeps the key in memory only until you lock Admin Mode or close the app. Treat it like a password, because it has full access to the database. If it ever leaks, rotate it on the same console page. Google marks these secrets as a legacy feature, so check that the page still offers them.

## Testing

`tests/test_firebase_rules.py` runs the rules on the official emulator. It replays what the current app sends, what older released versions send, and what an attacker would try. It needs Java and Node.js:

```bash
npx firebase-tools --config firebase/firebase.json emulators:exec --only database \
  --project demo-link-extractor "python -m pytest tests/test_firebase_rules.py"
```

The CI workflow runs the same command on every push. You can also try individual requests in the **Rules Playground** on the console's Rules tab.

## Writing patterns in the rules

Firebase rule patterns support less than JavaScript or Python, and some mistakes load fine but match the wrong things. Only the emulator tests show that a pattern works.

- `^` may appear only at the very start and `$` only at the very end. Put alternatives in one group, as in `^(a|b)?$`, where the trailing `?` also allows an empty string.
- There is no `\s` or `\S`. Inside a character class, `\t`, `\n`, `\r`, `\f` and `\v` are read as the plain letters t, n, r, f and v, so a class built from them rejects ordinary URLs.
- For "any character except whitespace", use `[!-�]`, written with the JSON escape `�` so Firebase receives the character itself. The range runs from `!` to U+FFFD, which leaves out spaces and every control character and allows accented and other non-ASCII text.
- `tests/test_firebase_rules_static.py` reads each pattern back with Python's `re` and compares it with `links.py`, so a pattern must mean the same thing in both.
