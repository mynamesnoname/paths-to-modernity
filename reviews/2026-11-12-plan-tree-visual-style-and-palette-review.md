# Plan Tree 2.5D Renderer — Visual Style & Palette Review

- **Date:** 2026-11-12
- **Scope:** `experiments/plan-tree/` — the rendered example (`output/tree.png`), styling and visual treatment in `tree_layout.py`
- **Review type:** Visual / aesthetic design. This is **not** a proposal to replace the layout algorithm.
- **Background note:** The PNG is transparent; the apparent black background in some viewers is not intended. The actual HTML canvas uses a light gray background.

## Executive assessment

The current renderer already has a distinct visual identity: a hybrid of an engineering architecture diagram, a planning blueprint, and restrained 2.5D information visualization. The LT → MT → ST → WP hierarchy is legible at the structural level, and the mixture of horizontal branching and vertically stacked WP leaves gives the overall diagram a recognizable silhouette.

**Retain the layout and the 2.5D concept. Refine the material language instead.** Aim for *Soft Technical / Architectural Minimalism*: precise orthogonal structure, gently colored status surfaces, subdued depth, and carefully weighted typography.

The review after seeing the actual image **revises** an earlier recommendation: do **not** remove status-tinted card backgrounds altogether. The distribution of pale green completed tasks is useful at a glance. The problem is the saturation and prominence of repeated borders, not the existence of status color.

### Design principle

> **Color indicates state. Geometry indicates structure. Contrast indicates attention.**

Do not give every visual channel competing responsibilities.

## What should stay

1. **Overall tree layout.** LT at the top, MT and ST as horizontal branches, WP as a hybrid horizontal/vertical arrangement.
2. **Vertical leaf stacking.** This limits width growth and produces a distinctive, readable pattern for dense branches.
3. **2.5D extrusion.** It meaningfully distinguishes this visualization from a standard flowchart; avoid eliminating it or making it a complex rotating 3D scene.
4. **Pale status fills.** The prevalence of completed tasks becomes spatially apparent.
5. **Generous negative space.** Do not artificially fill the right or bottom gaps merely for symmetry.

The full-tree view should remain available as the default overview. Future Focus/Collapse modes should be additive, not replacements for the existing silhouette.

## Visual issues and proposed treatments

### 1. Status borders compete with structure

The repeated green card borders form a strong visual rhythm, but begin to overshadow the content and tree topology, particularly in the long WP stacks.

**Change:** keep very light state-based fills, decrease border saturation and contrast, and reserve stronger strokes for selected/alert states.

| Status | Fill | Border | Suggested dark text |
| --- | --- | --- | --- |
| Done | `#EDF7F0` | `#A7CEB4` | `#234B36` |
| In Progress | `#FFF4E8` | `#E7BA91` | `#80512A` |
| Proposed | `#EFF5FC` | `#B3C9E2` | `#31577D` |
| Blocked | `#FCEEEE` | `#E0ACAC` | `#873F3F` |
| Superseded | `#F1F2F4` | `#C9CDD2` | `#777D85` |

Avoid highly saturated base-state outlines; those should denote interaction or exception.

### 2. 2.5D side faces are visually heavy

The current card height is `NODE_H = 68`, whereas the LT height offset is `z = 72`. In the rendered image, upper-level faces can appear as substantial blocks with a weight comparable to the front card.

**Experiment:** halve the extrusion and slightly reduce its horizontal shear:

| Level | Current z | Proposed z |
| --- | ---: | ---: |
| LT | 72 | 36 |
| MT | 48 | 24 |
| ST | 24 | 12 |
| WP | 0 | 0 |

```python
LEVEL_Z = {"long-term": 36, "mid-term": 24, "short-term": 12, "work-package": 0}
DEPTH_X = 0.35  # previously 0.45
```

This is a **visual experiment**, not a guaranteed optimal numeric setting. Compare full-tree screenshots at the same display size.

**Material:** prefer a neutral cool-gray side face rather than a darkened status fill:

- Subtle: side fill `#E7EAEE`, stroke `#D5DADF`
- Slightly stronger: side fill `#DDE1E5`, stroke `#C7CDD3`

Keep status meaning on the front face. Consider lighter contact shadows closer to the footprint rather than visually prominent oval shadows.

### 3. Level accents should be quieter

Level is already expressed by parent–child geometry and spatial position. Accent strips and LT/MT/ST/WP tags may remain, but use muted colors so they do not compete with status fills.

| Level | Suggested accent |
| --- | --- |
| LT | `#7766A6` |
| MT | `#6487AD` |
| ST | `#6F9DA2` |
| WP | `#A4ADB7` |

The accent should communicate hierarchy, not priority or progress.

### 4. Connectors resemble a conventional flowchart

The orthogonal routing is appropriate and should remain. But crisp, visually assertive corner transitions and dense shared-looking WP vertical lines make the diagram feel somewhat like a classic CAD/Visio flowchart.

**Change:**

```css
.edge {
  stroke: #B8C0C9;
  stroke-width: 1.2;
  stroke-linecap: round;
  stroke-linejoin: round;
}
```

If technically practical, test micro-rounded orthogonal turns (4–6 px radius). Avoid switching the whole tree to Bézier curves. Retain clear selected-route highlighting.

### 5. Card shape and typography

The current `card_path(..., radius=10)` is a little soft relative to the exact right-angle connections. Test `radius=5` for a more architectural, instrument-like feel.

The card label hierarchy needs strengthening:

- **ID:** 11px, medium-weight, lower contrast.
- **Title:** 13–14px, semibold, primary visual anchor.
- **Level tag:** 10px, muted, secondary.
- **Status:** primarily via pale fill; avoid requiring a prominent repeated status label.

Currently both ID and title are 12px, while ID is bold and the title is regular; this makes the identifier compete with the actual task description. Also improve wrapping: fixed-character splitting is fragile for English words and mixed CJK/Latin titles.

### 6. Canvas background

The PNG is transparent. In the HTML, `#F1F3F5` is used as the background. Consider:

- **Preferred warm neutral:** `#F6F6F4`
- **Alternative cool technical:** `#F5F7F8`

Avoid decorative grid backgrounds: the tree already contains substantial line geometry. Do not evaluate palette choices against the accidental black background produced by transparency viewers.

## Cohesive recommended palette

| Element | Color |
| --- | --- |
| Canvas | `#F6F6F4` |
| Neutral card | `#FFFFFF` |
| Main text | `#27313B` |
| Secondary text | `#78838D` |
| Tree edge | `#B8C0C9` |
| 2.5D side face | `#E1E5E8` |
| Done fill / border | `#EDF7F0` / `#A7CEB4` |
| In-progress fill / border | `#FFF4E8` / `#E7BA91` |
| Proposed fill / border | `#EFF5FC` / `#B3C9E2` |
| Blocked fill / border | `#FCEEEE` / `#E0ACAC` |
| Selected outline | `#5078B8` |

This palette is intended as a coherent baseline for visual comparison, not an immutable design system. Validate contrast and selection visibility at both 100% zoom and whole-tree fit.

## Ordered implementation recommendations

| Priority | Change | Expected benefit |
| --- | --- | --- |
| P1 | Softer status borders while retaining tinted fills | Less visual noise without losing overview information |
| P1 | Thinner, neutral-gray extrusion | More refined architectural quality |
| P1 | Clearer title / ID hierarchy and improved wrapping | Better legibility |
| P2 | Muted orthogonal connectors and optional micro-rounded corners | More consistent contemporary technical style |
| P2 | Slightly smaller card corner radius and lighter canvas background | Greater stylistic coherence |
| P2 | Quiet level accent colors and subtler shadows | Reduced competing signals |

## Acceptance / visual comparison protocol

When testing a proposed visual revision:

1. Render the **same 64-node snapshot** with the **same tree layout**; do not conflate palette feedback with layout changes.
2. Compare at (a) fit-to-screen overview, (b) 100% card scale, and (c) a dense vertically stacked WP branch.
3. Check whether one can quickly distinguish done, in-progress, proposed, blocked, and superseded **without** thick borders.
4. Check that LT/MT/ST depth remains perceptible without visually dominating the card front.
5. Check that the title is the first readable element of each card, before its ID and tag.
6. Confirm selected path / selected node has stronger contrast than ordinary state encoding.
7. Inspect against the **actual light canvas**, not transparency rendered as black.

## Conclusion

Do not turn this into a generic dashboard or a futuristic 3D viewer. Preserve the unmistakable stepped, stacked tree geometry. The strongest next step is **visual refinement without layout redesign**: subdued status strokes, light neutral extrusion, better typographic hierarchy, and restrained architectural detailing.

**Target character:** a carefully engineered scientific/project planning instrument rather than a colorful task-board UI.
