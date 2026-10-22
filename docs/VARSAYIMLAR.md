# Varsayımlar

> Bu dosya koddan üretilir: `tft-engine audit --write-docs`. Elle düzenleme; kaynağı `src/tft_engine/decision/assumptions.py` ve `tests/golden/p1/`. Güncel değilse denetim hata verir.

Oyun verisi olmayan her model sayısı burada. Hepsinin güven sınıfı `assumption`: ölçülmedi, motorun tahmini. Aralıklı olanlar P1'in hassasiyet raporunda iki ucuyla yeniden hesaplanır.

- **59 varsayım**, 43 tanesinin aralığı var, 15 tanesinin gerekçesi yazılı.
- P1'de en az bir senaryonun kararını çeviren: **12** varsayım.

## Kararı en çok çevirenler (P1 senaryoları)

| Varsayım | Senaryo sayısı | Senaryolar |
|---|---|---|
| `comp_complete_bonus` | 4 | b3_wisp_first_three_star, n3_three_star_3cost, n4_late_low_hp, o5_pivot_off_contested |
| `excess_gold_value_hp` | 4 | b3_wisp_first_three_star, n3_three_star_3cost, o2_nothing_to_hit_early, o4_cheap_level |
| `damage_scale` | 3 | b3_wisp_first_three_star, n3_three_star_3cost, n4_late_low_hp |
| `future_rounds` | 2 | b3_wisp_first_three_star, n3_three_star_3cost |
| `gold_value_hp` | 2 | b3_wisp_first_three_star, n3_three_star_3cost |
| `opp_strength_scale` | 2 | n4_late_low_hp, o4_cheap_level |
| `star_mult_2` | 2 | n4_late_low_hp, o4_cheap_level |
| `unit_power_cost_exp` | 2 | n4_late_low_hp, o4_cheap_level |
| `win_prob_slope` | 2 | b3_wisp_first_three_star, n3_three_star_3cost |
| `elim_penalty_hp` | 1 | n4_late_low_hp |
| `horizon_rounds` | 1 | n4_late_low_hp |
| `level_value_hp` | 1 | o2_nothing_to_hit_early |

## Tam liste

| Varsayım | Varsayılan | Aralık | Açıklama | Gerekçe | Nasıl doğrulanır | Kullanan |
|---|---|---|---|---|---|---|
| `horizon_rounds` | 3 | 2 – 4 | player-combat rounds looked ahead | yazılmadı | — | decision/horizon.py |
| `roll_floor` | 0 | 0 – 20 | rolling stops below this gold (candidates A and D) | yazılmadı | — | decision/evaluate.py |
| `unit_power_cost_exp` | 1.0 | 0.7 – 1.3 | unit power grows as cost ** this | yazılmadı | — | decision/strength.py |
| `star_mult_2` | 1.8 | 1.5 – 2.2 | 2-star unit power vs 1-star | yazılmadı | — | decision/strength.py |
| `star_mult_3` | 5.0 | 3.5 – 6.5 | 3-star unit power vs 1-star | yazılmadı | — | decision/strength.py |
| `comp_complete_bonus` | 0.15 | 0.0 – 0.3 | strength bonus when a target comp is done | yazılmadı | — | decision/strength.py |
| `win_prob_slope` | 4.0 | 2.0 – 6.0 | how fast win chance rises with strength ratio | yazılmadı | — | decision/strength.py |
| `opp_strength_scale` | 1.0 | 0.8 – 1.25 | multiplier on unseen opponents' strength | yazılmadı | — | decision/strength.py |
| `damage_scale` | 1.0 | 0.7 – 1.4 | multiplier on HP lost per lost round | yazılmadı | — | decision/horizon.py |
| `pool_depletion_scale` | 1.0 | 0.5 – 1.5 | multiplier on copies held by unseen boards | yazılmadı | — | decision/evaluate.py |
| `elim_penalty_hp` | 100.0 | 50.0 – 200.0 | cost of being eliminated, in HP | yazılmadı | — | decision/evaluate.py |
| `gold_value_hp` | 0.5 | 0.25 – 1.0 | value of 1 gold at the horizon end, up to the interest cap, in HP | yazılmadı | — | decision/evaluate.py |
| `excess_gold_value_hp` | 0.25 | 0.1 – 0.5 | value of 1 gold above the interest cap (earns no interest), in HP | yazılmadı | — | decision/evaluate.py |
| `level_value_hp` | 4.0 | 2.0 – 8.0 | value of 1 level at the horizon end, in HP | yazılmadı | — | decision/evaluate.py |
| `future_rounds` | 6 | 3 – 10 | rounds after the horizon in which the final board still decides fights | yazılmadı | — | decision/evaluate.py |
| `surviving_units_on_loss_by_stage` | {"1": 0, "2": 2, "3": 2, "4": 2, "5": 3, "6": 4… | — | enemy units left alive when a round is lost, by stage (damage = the set's stage damage + … | yazılmadı | — | decision/horizon.py |
| `opp_level_by_stage` | {"1": 3, "2": 4, "3": 6, "4": 7, "5": 8, "6": 8… | — | typical opponent level by stage | yazılmadı | — | decision/strength.py |
| `opp_unit_power_by_stage` | {"1": 1.0, "2": 1.6, "3": 3.2, "4": 5.0, "5": 6… | — | typical opponent unit power by stage, same scale as unit_power | yazılmadı | — | decision/strength.py |
| `tier_taken_frac_by_stage` | {"1": [0.05, 0.0, 0.0, 0.0, 0.0], "2": [0.15, 0… | — | share of other copies per cost held by unseen boards, by stage | yazılmadı | — | decision/evaluate.py |
| `item_fit_weights` | {"ad": {"ad_pct": 2, "as_pct": 1, "crit_pct": 1… | — | item fit rule weights by champion profile (rule-based, not statistics) | yazılmadı | — | decision/item_fit.py |
| `comp_match_weights` | {"units": 1.0, "items": 0.3, "unit_cost_exp": 1… | — | comp match score: share of the comp's units owned (weighted by cost ** unit_cost_exp) and… | yazılmadı | — | decision/comp_match.py |
| `sim_trait_bonus` | 0.1 | 0.05 – 0.15 | board power bonus per active trait breakpoint step (simulation) | yazılmadı | — | decision/board_builder.py, sim/game.py |
| `sim_level_curve` | {"2-1": 4, "2-5": 5, "3-2": 6, "3-5": 7, "4-2":… | — | stage at which the simulated player levels to at least this level | yazılmadı | — | sim/game.py |
| `sim_slow_roll_floor` | 50 | 30 – 50 | slow roll stays above this gold | owner's habit: slow roll above 50, may drop to 30 | — | sim/game.py |
| `sim_low_hp` | 40 | 25 – 55 | below this HP the simulated player rolls deep | yazılmadı | — | sim/game.py |
| `sim_deep_roll_floor` | 10 | 0 – 20 | gold kept when rolling deep | yazılmadı | — | sim/game.py |
| `sim_item_min_fit` | 2.0 | 1.0 – 3.0 | below this fit no holder suits the item: keep the components | yazılmadı | — | sim/game.py |
| `sim_no_items_before` | 2-1 | — | no items are crafted before this round (owner: stage 1 is won anyway) | owner's review of a simulated game | — | sim/game.py |
| `sim_lose_streak_hp` | 60 | 50 – 75 | early loss streak (or Coven) keeps saving gold while HP is at least this | yazılmadı | — | sim/game.py |
| `sim_rolldown_floor` | 20 | 10 – 30 | gold kept in the level 8 roll-down (from 4-2) | yazılmadı | — | sim/game.py |
| `sim_excess_gold` | 60 | 50 – 80 | above this gold, spend the excess on XP or rolls | yazılmadı | — | sim/game.py |
| `sim_trait_progress` | 1.0 | 0.5 – 2.0 | weight of trait progress among all owned units when buying | yazılmadı | — | sim/game.py |
| `sim_shop_trait_weight` | 2.0 | 1.0 – 3.0 | extra weight of breakpoints that change the shop (5 Riftbeast, 5 Blossom) | yazılmadı | — | sim/game.py |
| `sim_components_per_monster_round` | 2 | 1 – 3 | components dropped by each x-7 monster round (owner: many items drop) | owner's review of a simulated game | count drops in a few real games (templates/oyun_ici_kontrol… | sim/game.py |
| `sim_carousel_round` | 4 | — | round x-4 is a carousel giving one component (no champion modelled) | yazılmadı | — | sim/game.py |
| `sim_carry_needs_items_value` | 0.5 | 0.25 – 1.0 | share of a 4-5 cost carry's value when the held items do not suit it | yazılmadı | — | sim/game.py |
| `sim_one_short_step` | 0.5 | 0.25 – 0.75 | trait step value counted when one unit short of the next breakpoint | guess (simulation policy, 2026-10-21) | — | sim/game.py |
| `sim_trait_value_floor` | 3.0 | 1.0 – 5.0 | board power floor used to value trait progress early in the game | guess (simulation policy, 2026-10-21) | — | sim/game.py |
| `sim_pair_value` | 0.3 | 0.1 – 0.5 | value of a copy toward a star-up, as a share of the unit's cost | guess (simulation policy, 2026-10-21) | — | sim/game.py |
| `sim_star_up_value` | 0.5 | 0.25 – 1.0 | least value of a buy that completes a star-up, share of the unit's cost | guess (simulation policy, 2026-10-21) | — | sim/game.py |
| `sim_interest_break_gain` | 0.15 | 0.05 – 0.3 | gain (share of board power) worth dropping below an interest step | guess (simulation policy, 2026-10-21) | — | sim/game.py |
| `sim_item_holder_weight` | 0.1 | 0.0 – 0.3 | weight of a holder's unit value next to item fit when crafting | guess (simulation policy, 2026-10-21) | — | sim/game.py |
| `sim_survivor_share` | 0.3 | 0.2 – 0.5 | share of the winner's board alive after an even fight (simulation) | guess (simulation combat, 2026-10-21) | — | sim/game.py |
| `sim_idle_holder_factor` | 0.6 | 0.4 – 1.0 | item fit multiplier for a holder that adds to no active trait | yazılmadı | — | sim/game.py |
| `power_fight_seconds` | 20 | 15 – 30 | length of a typical player combat | yazılmadı | — | decision/board_power.py |
| `power_mana_per_attack` | 10 | 5 – 10 | mana gained per attack (not in the game data) | yazılmadı | — | decision/board_power.py |
| `power_ability_base` | {"1": 250, "2": 330, "3": 420, "4": 550, "5": 7… | — | ability damage per cast of a 1-star carry at base AD/AP, by cost (stand-in until ability … | yazılmadı | — | decision/board_power.py |
| `power_ability_star` | {"1": 1.0, "2": 1.5, "3": 2.5} | — | ability value per star relative to 1-star | yazılmadı | — | decision/board_power.py |
| `power_tank_ability_share` | 0.6 | 0.3 – 1.0 | share of a tank's ability value counted as extra Health (shields, heals) | yazılmadı | — | decision/board_power.py |
| `power_resist_weight` | 1.0 | 0.7 – 1.3 | how much average Armor/MR raise effective Health: hp x (1 + w x resist/100) | yazılmadı | — | decision/board_power.py |
| `power_attack_count_mana` | 5 | 3 – 10 | a mana bar this small counts attacks (every third attack ...), not mana | guess from Caitlyn and Master Yi texts (2026-10-21) | in game: how often a 3-mana unit casts | decision/board_power.py |
| `power_min_cast_seconds` | 1.5 | 1.0 – 2.5 | at most one cast every this many seconds (cast time, mana lock) | guess (2026-10-21) | — | decision/board_power.py |
| `power_default_crit_mult` | 1.4 | — | crit damage multiplier when a champion record has none | guess; CommunityDragon records usually carry critMultiplier | — | decision/board_power.py |
| `power_min_damage_taken` | 0.1 | — | durability never reduces damage taken below this share (guard) | guess; keeps effective Health finite | — | decision/board_power.py |
| `build_cost_caps` | {"7": {"4": 2, "5": 0}, "8": {"4": 4, "5": 1}, … | — | most 4- and 5-cost units a board can hold at a level (from shop odds) | yazılmadı | — | decision/board_builder.py |
| `build_stars` | {"7": {"1": 2, "2": 2, "3": 2, "4": 1, "5": 1},… | — | star level assumed per unit cost at a level | yazılmadı | — | decision/board_builder.py |
| `build_item_slots` | [3, 3, 2] | — | items for the main carry, the main tank and a second carry | yazılmadı | — | decision/board_builder.py |
| `wisp_shop_prob` | null | 0.25 – 1.0 | chance a shop shows a Wisp (None = set data: every other shop) | set data shop rule wisp_slot; owner's observation 18.4b | count Wisp shops over many rolls in game | decision/evaluate.py |
| `wisp_price` | 1 | 0 – 3 | gold paid for the cheapest Wisp when buying one to roll | yazılmadı | — | decision/evaluate.py |
