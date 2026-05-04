# OMNI-SIM FPS Mission DSL v1

This directory holds **mission packs** — JSON documents that fully describe one
FPS training campaign for the OMNI-SIM platform. The pre-compiled FPS engine
under `backend/static/game/assets/index-*.js` reads exactly one of these
documents at boot (via `window.__GAME_MISSION__`) and renders it. **No engine
recompile is required to author a new training topic.**

## Files

| Path | Purpose |
|------|---------|
| `_schema/fps-mission-v1.schema.json` | JSON Schema (Draft-07) — the contract. |
| `smartx-v2v-fps-v1.json` | Pack 1 — the original "数据中心攻坚战 / SmartX V2V 迁移" content extracted from code (`MissionNarrator.ts`, `TutorialPrompts.ts`, `MissionObjects.ts`, `phases/*.ts`). 9 acts. |
| `smartx-hci-iops-fps-v1.json` | Pack 2 — "HCI 性能调优实战 · NVMe IOPS 攻坚". Validates that the same engine + DSL renders a totally different topic. 5 acts. |

## Layered template

```
L1  通用 FPS 引擎核心   (src/fps/*, src/engine/*, src/ui/IntroVideo.tsx, ...)
L2  可装配组件库         (Interactable factory: console / deploy_pad / hologram / ...
                        Phase types: scan / config / quiz / sync / validate / cutover / combat
                        Validators:  threshold / regex / equal / external_tool)
L3  Mission DSL v1      ← this directory
L4  示例数据包           smartx-v2v-fps-v1.json + smartx-hci-iops-fps-v1.json
```

The mapping from old hardcoded sites to DSL fields:

| Hardcoded code site | DSL field |
|---|---|
| `index.html` `<title>` "数据中心攻坚战 · SmartX FPS" | `meta.name` (loader auto-replaces `<title>`) |
| `IntroVideo.tsx` `src='/intro.mp4'` | `intro.videoUrl` + `intro.subtitles[]` + `intro.skippable` |
| `RealisticDataCenter.ts` 机柜布局 | `scene.preset` ∈ `datacenter_small / medium / large / lab / office / warehouse` + `scene.decor[]` |
| `phases/EnvScanPhase.ts` … `PostCheckPhase.ts` (8 classes) | `acts[].type` + `acts[].config` (one `GenericPhase` reads them) |
| `MissionNarrator.ts` `ACT1_DEPLOY` … `ACT9_DONE` | `acts[].id` + `acts[].narration{title, subtitle, objective, briefing, hint}` |
| `TutorialPrompts.ts` `ACT_SOP_TIPS` (vCenter/VLAN/IOPS knowledge) | `acts[].sopTips[]` |
| `TutorialPrompts.ts` `PLAY_TIPS` (weapon/pickup tips) | `tutorialTips[]` |
| `MissionObjects.DeployPad` / `VMHologram` (new'd from code) | `scene.interactables[]` (declarative) |
| `migration.py::_default_mission_for` (vmId/vmName/dataTotalGB hardcoded) | `meta.vars{}` (any string can use `{{varName}}`) |
| Fixed Soldier.glb / smg.glb paths | `scene.characters[].modelUrl` / `scene.weapons[].modelUrl` |

## E-key interaction model

The engine's `InteractionSystem.ts` (raycast on `KeyE`) **stays unchanged**.
What it dispatches is now data-driven:

```jsonc
"interactables": [
  {
    "id":          "console_scan",
    "type":        "console",
    "position":    [3.5, 0, -2.0],
    "color":       "#00E676",
    "label":       "vCenter 控制台",
    "hoverPrompt": "按 E 启动兼容性扫描",   // replaces the generic "按 E 交互"
    "visibleIf":   { "varsEqual": { "deployComplete": true } },
    "onInteract":  {
      "advancePhase":  "act3_scan",          // drive the state machine
      "openTerminal":  "vddk-cli",           // OR open a fake CLI modal
      "openQuiz":      "q_compat_check",     // OR open inline quiz
      "playVideo":     "/clips/scan-explainer.mp4",
      "setVar":        { "scannerEquipped": true },
      "playSound":     "console_beep",
      "requireVar":    { "deployComplete": true }
    }
  }
]
```

The same E-key prompt → "**按下 E 后跑哪段培训内容**" is now expressed as data.
For V2V it's "openTerminal: vddk-cli"; for IOPS it's "openTerminal: fio"; for
security it could be "openQuiz: phishing_drill". The engine doesn't change.

## How a Level picks a mission pack

1. **Per-level config (preferred)** — the platform `Level.config`:
   ```json
   { "mission_pack": "smartx-hci-iops-fps-v1" }
   ```
   `GET /api/migration/levels/{id}/mission` then includes
   `"missionPack": "smartx-hci-iops-fps-v1"` and the React `Game.tsx` page
   forwards it to the iframe.

2. **URL override (preview / QA)** — visit
   `/learn/levels/<id>?missionPack=smartx-hci-iops-fps-v1` in the platform UI.

3. **Implicit default** — when nothing is set, backend resolves to
   `smartx-v2v-fps-v1`, so existing courses keep working unchanged.

## Loading flow

```
Platform Game.tsx                  Backend                  FPS bundle (iframe)
─────────────────                  ───────                  ──────────────────
GET /api/migration/levels/42/mission
        │
        ▼
   resolves Level.config.mission_pack
   → "smartx-hci-iops-fps-v1"
        │
        ▼
iframe src=/game/index.html?...&missionPack=smartx-hci-iops-fps-v1
                                                                 │
                                                                 ▼
                                            <script> in index.html
                                            fetches /game/missions/<id>.json
                                            sets window.__GAME_MISSION__
                                            sets document.title
                                                                 │
                                                                 ▼
                                            engine bundle reads __GAME_MISSION__
                                            and renders intro/scene/acts.
```

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/missions` | List published mission packs (id + meta only). |
| GET | `/api/missions/{pack_id}` | Full mission JSON. |
| GET | `/api/migration/levels/{level_id}/mission` | Resolves a Level → mission-pack id (used by `Game.tsx`). |
| GET | `/game/missions/{pack_id}.json` | Static fallback (same JSON, no auth). |

## Authoring a new pack

1. Copy `smartx-hci-iops-fps-v1.json` (smaller / simpler example).
2. Change `id`, `meta.name`, `meta.domain`.
3. Adjust `intro.videoUrl` (drop the new mp4 alongside the JSON).
4. Replace `scene.interactables[]` and `acts[]` with your topic's content.
5. Validate against the schema:
   ```bash
   python3 -c "import json,jsonschema; \
     jsonschema.validate(json.load(open('your-pack.json')), \
                         json.load(open('_schema/fps-mission-v1.schema.json')))"
   ```
6. Either drop the JSON in this directory (static loader serves it) or
   bind it to a Level via `Level.config.mission_pack = "your-pack-id"`.

## Engine hand-off (still pending)

The engine source tree (`src/fps/*`, `src/engine/*`, `src/simulation/phases/*`)
lives in a separate repo and is **not in this repository**. To complete the
data-driven migration, the engine work needed is:

1. Read `window.__GAME_MISSION__` (already populated by `index.html`) at boot.
2. Replace the 8 `phases/*.ts` classes with one `GenericPhase` whose `start()`
   dispatches on `act.type` (`scan / config / quiz / sync / validate / cutover / combat`).
3. `MissionNarrator.ts`: drop the `ACT1..9` enum + literals; iterate
   `mission.acts[]` instead.
4. `TutorialPrompts.ts`: drop `PLAY_TIPS` / `ACT_SOP_TIPS` constants; load from
   `mission.tutorialTips[]` and `act.sopTips[]`.
5. `MissionObjects.ts`: replace direct `new DeployPad()` / `new VMHologram()`
   with `InteractableFactory.create(spec)` driven by `mission.scene.interactables[]`.
6. `IntroVideo.tsx`: read `mission.intro.videoUrl` instead of `'/intro.mp4'`.
7. `RealisticDataCenter.ts`: select preset from `mission.scene.preset`.

Each item above corresponds to a single field in this DSL. The contract is
stable; the engine refactor can land in a follow-up release without breaking
mission-pack authors.
