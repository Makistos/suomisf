# Antikvaari Price Matching

Price matching connects Antikvaari listings to owned editions and expresses
how reliable a price estimate is as a quality level.

## Quality levels

| Level   | Meaning |
|---------|---------|
| Perfect | Same edition, same condition |
| Good    | Same edition, condition 1 step off — or close edition, same condition |
| Decent  | Same edition, condition 2+ steps off — or close edition, 1 step off |
| Poor    | Very different edition or condition |

## Edition match (`_edition_match_level`)

When a price row is matched against an edition the following fields are
compared in order:

1. **Laitos** (`edition.version` vs `product_laitos`): must match exactly
   when both are known; mismatch → `not_close`.
2. **Painos** (`edition.editionnum` vs `antikvaari_product_version`): must
   match exactly when both are known; mismatch → `not_close`.
3. **Binding** (`edition.binding_id` vs `antikvaari_product_binding`): must
   match when both sides have a known binding (>1); mismatch → `not_close`.
4. **Year** (`edition.pubyear` vs `antikvaari_product_year`):
   - difference > 10 → `not_close`
   - difference 1–10 → `close`
   - difference 0 (or year unknown) → contributes to `same`

Result is `same`, `close`, or `not_close`.

## Quality calculation (`calculate_match_quality`)

Given an edition match level and a target condition (user's copy condition):

| Edition level | Condition diff | Quality |
|---------------|---------------|---------|
| `same`        | 0             | Perfect |
| `same`        | 1             | Good    |
| `same`        | 2+            | Decent  |
| `close`       | 0             | Good    |
| `close`       | 1             | Decent  |
| `close`       | 2+            | Poor    |
| `not_close`   | any           | Poor    |

When no target condition is supplied (user's condition unknown):

| Edition level | Quality |
|---------------|---------|
| `same`        | Good    |
| `close`       | Decent  |
| `not_close`   | Poor    |

## Close-edition fallback

When an owned edition has **no stored prices at all**, the system looks for a
*sibling* edition of the same work that:

- Has the same `version` (laitos), including both `NULL`
- Has a `pubyear` within 10 years of the owned edition
- Has at least one stored price

Among qualifying siblings the one with the **smallest year difference** wins.

Quality is calculated against the **sibling edition** (because the price was
matched to it at save time), then **downgraded** for the edition difference:

| Sibling binding vs owned binding | Downgrade |
|----------------------------------|-----------|
| Same explicit binding            | 1 level   |
| Different or unknown binding     | 2 levels  |

Downgrade steps: Perfect → Good → Decent → Poor (floor at Poor).
The result can therefore **never be Perfect**.

Exact-edition prices always take priority: the fallback is only tried when
the exact edition has zero stored prices, regardless of the quality that
those prices would yield.

## Where matching runs

| Location | Purpose |
|----------|---------|
| `impl_pricing.calculate_match_quality` | Core quality calculation used everywhere |
| `impl_pricing.edition_prices_get` | Per-edition price list shown in the prices dialog |
| `impl_pricing.user_collection_stats` | Collection value summary (totals, distribution) |
| `impl_editions._attach_best_prices` | Best price per owned book shown in the owned-books list |

The close-edition fallback runs in `user_collection_stats` and
`_attach_best_prices`; `edition_prices_get` shows only prices stored for the
exact edition.
