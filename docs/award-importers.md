# Awards, categories and importer status

Living reference of every award in the database, the categories linked to
it, and whether a winner **importer** exists for it. Update the
**Importer** column as importers are built.

- **Category type** (from `awardcategory.type`): `[0]` personal / lifetime,
  `[1]` novel / work, `[2]` short story.
- **Importer** values:
  - `ISFDB (n)` — covered by the ISFDB scraper; `n` = number of ISFDB
    award-category pages seeded in `award_import_source`.
  - `—` — no importer yet.
  - `personal only` — award has only a personal/lifetime category; no
    per-work/story winners to scrape.
- **Categories** column lists the categories linked via the
  `awardcategories` junction table. This junction is **incompletely
  populated**: some ISFDB-covered awards show no categories here even
  though the importer will attach winners (e.g. Apollo, British Fantasy,
  Goodreads, Imaginaire, Kurd Lasswitz, Premio Ignotus, Retro Hugo). The
  authoritative per-award category coverage for the ISFDB importer lives
  in `award_import_source.our_category`.

## Foreign awards

| ID | Award | Importer | Categories (junction) |
|----|-------|----------|-----------------------|
| 27 | Apollo | ISFDB (1) | — |
| 5 | Arthur C. Clarke -palkinto | ISFDB (1) | Paras romaani [1] |
| 20 | Bram Stoker Award | ISFDB (10) | Paras antologia [1], Paras romaani [1], Paras novelli [2] |
| 26 | British Fantasy Award | ISFDB (8) | — |
| 6 | British Science Fiction Award | ISFDB (4) | Paras romaani [1], Paras novelli [2] |
| 10 | Campbell Memorial Award | ISFDB (1) | Paras romaani [1] |
| 24 | Carnegie-mitali | ISFDB (1) | Paras nuortenkirja [1] |
| 1 | Damon Knight Memorial Grand Master Award | personal only | Elämäntyöpalkinto [0] |
| 29 | Goodreads Choice Awards | ISFDB (8) | — |
| 2 | Hugo | ISFDB (2) | Paras pienoisromaani [1], Paras romaani [1], Paras novelli [2], Paras pitkä novelli [2] |
| 31 | Imaginaire | ISFDB (3) | — |
| 32 | Kurd Lasswitz Preis | ISFDB (2) | — |
| 4 | Locus | ISFDB (13) | Paras antologia [1], Paras ensiromaani [1], Paras fantasiaromaani [1], Paras kauhuromaani [1], Paras kokoelma [1], Paras nuortenkirja [1], Paras pienoisromaani [1], Paras romaani [1], Paras scifi-romaani [1], Paras novelli [2], Paras pitkä novelli [2] |
| 21 | Mythopoeic | ISFDB (4) | Paras nuortenkirja [1], Paras romaani [1] |
| 3 | Nebula | ISFDB (5) | Paras pienoisromaani [1], Paras romaani [1], Paras novelli [2], Paras pitkä novelli [2] |
| 25 | Nobelin kirjallisuuspalkinto | personal only | Elämäntyöpalkinto [0] |
| 11 | Philip K. Dick Award | ISFDB (1) | Paras romaani [1] |
| 33 | Premio Ignotus | ISFDB (3) | — |
| 30 | Retro Hugo | ISFDB (4) | — |
| 7 | Sidewise | ISFDB (2) | Elämäntyöpalkinto [0], Paras romaani [1], Paras novelli [2] |
| 9 | Skylark | personal only | Elämäntyöpalkinto [0] |
| 12 | Theodore Sturgeon Award | ISFDB (1) | Paras novelli [2] |
| 34 | WHC Grand Master | — | — |
| 19 | World Fantasy Award | ISFDB (7) | Elämäntyöpalkinto [0], Paras antologia [1], Paras kokoelma [1], Paras pienoisromaani [1], Paras romaani [1], Paras novelli [2] |

## Domestic (Finnish) awards

Not on ISFDB; will need a different source (kirjasampo / Wikipedia).

| ID | Award | Importer | Categories (junction) |
|----|-------|----------|-----------------------|
| 13 | Atorox | — | Paras novelli [2] |
| 22 | Finlandia-palkinto | — | Paras romaani [1] |
| 18 | Kosmoskynä | — | Elämäntyöpalkinto [0] |
| 15 | Kuvastaja | — | Paras romaani [1] |
| 36 | Lasten- ja nuortenkirjallisuuden Finlandia | — | — |
| 17 | Nova-novellikilpailu | — | Paras novelli [2] |
| 16 | Portin novellikilpailu | — | Paras novelli [2] |
| 23 | Topelius-palkinto | — | Paras nuortenkirja [1] |
| 14 | Tähtifantasia | — | Paras romaani [1] |
| 8 | Tähtivaeltaja | — | Paras romaani [1] |

## Notes

- **Mixed personal + work/story:** Sidewise (7) and World Fantasy Award
  (19) have both a personal `Elämäntyöpalkinto` category and work/story
  categories. The ISFDB importer only handles work/story winners; their
  personal (person) winners must be left untouched — World Fantasy already
  has 48 person-awarded rows recorded.
- **Personal-only foreign awards** (Grand Master, Nobel, Skylark) have no
  per-work winners to scrape from ISFDB.

## Status summary

- ISFDB importer: **20** foreign awards seeded (`award_import_source`, 81
  category pages).
- Domestic importers: **0** (todo).
- Personal-award import: not implemented.
