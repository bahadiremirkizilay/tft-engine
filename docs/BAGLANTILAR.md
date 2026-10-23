# Bağlantılar

> Bu dosya koddan üretilir: `tft-engine audit --write-docs`. Elle düzenleme; kaynağı kodun kendisi (`src/`, `tools/`) ve `data/sets/*`. Güncel değilse denetim hata verir.

Bir şeyi değiştirmeden önce buraya bak: o parametreyi, dosyayı ya da modülü kim kullanıyor? Değişiklikten sonra bu kullananların testleri ve altın çıktıları kontrol edilir.

## Veri parametreleri → okuyan kod

| Parametre | Okuyan | Not |
|---|---|---|
| `bad_luck_protection` | — | value is false: no such field in the Set 18 game file |
| `base_income` | rules/economy.py |  |
| `champions_per_cost` | cli.py, decision/evaluate.py, gamedata/cdragon.py, gamedata/entities.py |  |
| `copies_per_champion` | cli.py, decision/evaluate.py, sim/game.py |  |
| `emblem_on_same_trait_counts` | cli.py, decision/evaluate.py, rules/board_stats.py, sim/game.py |  |
| `inferno_upgrade` | — | the roll solver already counts the shown shop; open questions in the param note |
| `interest_cap` | decision/horizon.py, rules/economy.py, rules/modifiers.py, sim/game.py |  |
| `interest_per_10_gold` | decision/horizon.py, rules/economy.py, sim/game.py |  |
| `max_level` | rules/economy.py, sim/game.py |  |
| `passive_xp_per_round` | rules/economy.py, sim/game.py |  |
| `player_damage` | rules/economy.py |  |
| `pvp_win_gold` | rules/economy.py |  |
| `reroll_cost` | cli.py, decision/evaluate.py, rules/economy.py, sim/game.py |  |
| `riftbeast_shop` | sim/game.py |  |
| `sell_value` | rules/economy.py |  |
| `shop_holds_copies` | — | owner's shop rule (07f551d); needs an opponent-shop belief layer |
| `shop_odds` | decision/evaluate.py, prob/shop_model.py, sim/game.py |  |
| `shop_slots` | prob/shop_model.py, sim/game.py |  |
| `star_multipliers` | decision/board_builder.py, rules/board_stats.py, sim/game.py |  |
| `streak_gold` | rules/economy.py |  |
| `wisp_slot` | prob/shop_model.py, sim/game.py |  |
| `xp_purchase` | rules/economy.py |  |
| `xp_to_next_level` | rules/economy.py |  |

## Curated dosyalar → yükleyen kod

| Klasör / dosya | Yükleyen | Not |
|---|---|---|
| `abilities` | gamedata/curated.py |  |
| `augment_tiers` | gamedata/curated.py, tools/curate_augment_tiers.py |  |
| `cdragon_rules` | tools/import_cdragon.py |  |
| `champion_roles` | gamedata/curated.py |  |
| `comps` | cli.py, decision/scenario.py, rules/comps.py |  |
| `effects` | decision/effects.py, decision/item_effects.py, gamedata/cdragon.py, gamedata/curated.py, gamedata/entities.py, rules/board_stats.py, tools/curate_item_stats.py |  |
| `item_effects` | decision/item_effects.py, gamedata/curated.py |  |
| `item_stats` | gamedata/curated.py, tools/curate_item_stats.py |  |
| `meta` | rules/comps.py |  |
| `overrides` | gamedata/curated.py, gamedata/entities.py |  |

## Modüller → kullananlar

| Modül | Kullanan |
|---|---|
| `tft_engine` | — |
| `audit` | cli |
| `audit.core` | audit, audit.data, audit.docs, audit.layers, audit.registry, audit.source_scan, audit.wiring, cli |
| `audit.data` | audit.core, cli |
| `audit.docs` | audit.core |
| `audit.layers` | audit.core |
| `audit.registry` | audit.docs, cli |
| `audit.source_scan` | audit.core, audit.layers, audit.wiring |
| `audit.wiring` | audit.core, audit.registry |
| `cli` | __main__ |
| `decision` | cli |
| `decision.assumptions` | audit.registry, audit.wiring, cli, decision, decision.board_builder, decision.board_power, decision.comp_match, decision.evaluate, decision.horizon, decision.item_effects, decision.item_fit, decision.strength, sim.game |
| `decision.board_builder` | — |
| `decision.board_power` | decision.board_builder, sim.game |
| `decision.comp_match` | cli |
| `decision.effects` | decision, decision.evaluate, decision.scenario |
| `decision.evaluate` | decision, decision.report |
| `decision.horizon` | decision.evaluate |
| `decision.item_effects` | decision.board_power |
| `decision.item_fit` | cli, decision.board_builder, decision.board_power, decision.comp_match, decision.item_effects, sim.game |
| `decision.report` | cli |
| `decision.scenario` | decision, decision.evaluate, decision.report |
| `decision.strength` | decision.evaluate, decision.horizon, sim.game |
| `experiments` | cli |
| `experiments.examples` | experiments.runner |
| `experiments.record` | experiments, experiments.runner |
| `experiments.runner` | experiments, experiments.examples |
| `gamedata` | cli, decision.board_builder, decision.effects, decision.evaluate, prob.shop_model, rules.economy, rules.modifiers, sim.game |
| `gamedata.cdragon` | gamedata.entities, tools/ |
| `gamedata.curated` | audit.wiring, gamedata.entities |
| `gamedata.entities` | audit.data, cli, decision.evaluate, sim.game, tools/ |
| `gamedata.hashes` | gamedata.cdragon |
| `gamedata.loader` | audit.data, gamedata, gamedata.entities |
| `gamedata.schema` | gamedata, gamedata.cdragon, gamedata.curated, gamedata.entities, gamedata.loader, gamedata.sources, rules.board_stats, rules.comps, rules.items |
| `gamedata.sources` | audit.data, gamedata.entities, tools/ |
| `prob` | cli, decision.evaluate |
| `prob.exact` | prob, prob.sampler |
| `prob.query` | prob, prob.exact, prob.sampler |
| `prob.sampler` | prob |
| `prob.shop_model` | prob, prob.exact, prob.sampler |
| `repro` | decision.evaluate, experiments.examples, prob.sampler, sim.game |
| `repro.seeds` | repro |
| `rules` | decision.evaluate, decision.horizon, sim.game |
| `rules.board_stats` | audit.data, audit.wiring, decision.board_builder, decision.board_power, sim.game |
| `rules.comps` | audit.data, cli, decision.comp_match |
| `rules.economy` | rules |
| `rules.items` | cli, decision.board_builder, decision.comp_match, rules.board_stats, rules.traits, sim.game |
| `rules.modifiers` | decision.effects, decision.evaluate, rules.economy |
| `rules.traits` | cli, decision.board_builder, decision.evaluate, rules.board_stats, sim.game |
| `sim` | cli |
| `sim.game` | sim |
| `state` | cli, decision.effects, decision.evaluate, decision.horizon, decision.scenario, decision.strength, prob.exact, prob.sampler, rules.economy, sim.game |
| `state.game_state` | decision.scenario, sim.game, state |
| `state.pool` | state |

Kabul edilen istisnalar ve bilinen borçlar: [audit.toml](../audit.toml).
