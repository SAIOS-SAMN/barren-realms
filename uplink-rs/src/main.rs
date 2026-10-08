//! barren-realms' solve client. One request on stdin (JSON), one verdict on stdout (JSON):
//!
//!   {"addr": "127.0.0.1:7500", "key": "<path to the voice's raw 32-byte ed25519 seed>",
//!    "task_id": "<hex>", "train": [[in, out], ...], "outputs": [grid, ...],
//!    "steps": [{"motion": "Rotate90"} | {"hue": [[from, to], ...]}, ...]}
//!
//! Each motion is the centred rigid motion `Step::grid_motion` builds for the shapes it acts between, traced through
//! the steps on the family's first input; a hue step names every hue it moves. The steps are minted through the one
//! mint (`rule::sentence`), checked by the judge's own steps (`rule::would_judge`), and submitted signed by the voice
//! (`Entity::solve_task`, which crosses the rule and replays it at home first). Nothing is forged here.

use std::io::Read;

use mycelium::sdk::rule::{sentence, would_judge, Extent, Pred, Region, Step, Symmetry};
use mycelium::sdk::{Entity, Kernel};
use serde::Deserialize;
use serde_json::json;

type Grid = Vec<Vec<u8>>;

#[derive(Deserialize)]
#[serde(rename_all = "snake_case")]
enum StepIn {
    Motion(String),
    Hue(Vec<(u8, u8)>),
    /// The size crystals (78.143): scale by up/down; select the bodies of a hue, then crop to the one selected.
    Scale((u8, u8)),
    SelectHue(u8),
    Crop(String),
    /// The region crystal (78.143): select every body, take its interior, and the hue step after fills it.
    SelectAll(bool),
    Region(String),
}

#[derive(Deserialize)]
struct Request {
    addr: String,
    key: String,
    task_id: String,
    train: Vec<(Grid, Grid)>,
    outputs: Vec<Grid>,
    steps: Vec<StepIn>,
}

fn symmetry(name: &str) -> Option<Symmetry> {
    Some(match name {
        "Rotate90" => Symmetry::Rotate90,
        "Rotate180" => Symmetry::Rotate180,
        "Rotate270" => Symmetry::Rotate270,
        "FlipH" => Symmetry::FlipH,
        "FlipV" => Symmetry::FlipV,
        "Transpose" => Symmetry::Transpose,
        _ => return None,
    })
}

fn shape(g: &Grid) -> (usize, usize) {
    (g.len(), g.first().map_or(0, |r| r.len()))
}

fn moved(kind: Symmetry, (r, c): (usize, usize)) -> (usize, usize) {
    match kind {
        Symmetry::Rotate90 | Symmetry::Rotate270 | Symmetry::Transpose => (c, r),
        _ => (r, c),
    }
}

fn hex(s: &str) -> Option<Vec<u8>> {
    (0..s.len()).step_by(2).map(|i| u8::from_str_radix(s.get(i..i + 2)?, 16).ok()).collect()
}

fn out(v: serde_json::Value) {
    println!("{v}");
}

fn main() {
    let mut raw = String::new();
    if std::io::stdin().read_to_string(&mut raw).is_err() {
        return out(json!({"error": "no request on stdin"}));
    }
    let req: Request = match serde_json::from_str(&raw) {
        Ok(r) => r,
        Err(e) => return out(json!({"error": format!("request: {e}")})),
    };
    // wire v1.2: a task is named by its 32-byte citation
    let Some(id) = hex(&req.task_id).and_then(|v| <[u8; 32]>::try_from(v).ok()) else {
        return out(json!({"error": "task_id is not a 32-byte citation"}));
    };
    let seed: [u8; 32] = match std::fs::read(&req.key).ok().and_then(|b| b.try_into().ok()) {
        Some(s) => s,
        None => return out(json!({"error": "the voice's key is not a 32-byte seed"})),
    };
    let Some(first) = req.train.first() else { return out(json!({"error": "no family"})) };
    // the steps, each motion built for the shapes it acts between
    let mut at = shape(&first.0);
    let mut steps = Vec::with_capacity(req.steps.len());
    for s in &req.steps {
        match s {
            StepIn::Motion(name) => {
                let Some(kind) = symmetry(name) else { return out(json!({"error": format!("no such motion: {name}")})) };
                let next = moved(kind, at);
                let Some(step) = Step::grid_motion(kind, at, next) else {
                    return out(json!({"verdict": "unminted", "why": format!("{name} cannot act between {at:?} and {next:?}")}));
                };
                steps.push(step);
                at = next;
            }
            StepIn::Hue(map) => steps.push(Step::Hue(map.clone())),
            StepIn::Scale((up, down)) => {
                steps.push(Step::Scale { up: *up, down: *down });
                at = (at.0 * usize::from(*up) / usize::from((*down).max(1)), at.1 * usize::from(*up) / usize::from((*down).max(1)));
            }
            StepIn::SelectHue(h) => steps.push(Step::Select(Pred::Hue(*h))),
            StepIn::Crop(e) => steps.push(Step::Crop(if e == "interior" { Extent::Interior } else { Extent::Body })),
            StepIn::SelectAll(_) => steps.push(Step::Select(Pred::All)),
            StepIn::Region(r) => steps.push(Step::Region(match r.as_str() {
                "halo" => Region::Halo,
                "extent" => Region::Extent,
                _ => Region::Interior,
            })),
        }
    }
    let kernel = Kernel::from_key(ed25519_dalek::SigningKey::from_bytes(&seed));
    let mut entity = Entity::open(&req.addr, kernel);
    let rule = match sentence(&steps, &req.train, &entity.epigenome) {
        Ok(r) => r,
        Err(why) => return out(json!({"verdict": "unminted", "why": format!("{why:?}")})),
    };
    let resolve = |a: &[u8]| entity.epigenome.working_word(a).and_then(|e| e.form().cloned());
    if let Err(why) = would_judge(&rule, &req.train, &resolve, &entity.epigenome) {
        return out(json!({"verdict": "refuted_at_home", "why": format!("{why:?}")}));
    }
    let mut budget = entity.physics_mut().stroke();
    match entity.solve_task(&id, &req.train, &req.outputs, Some(&rule), &mut budget) {
        Some((code, mu)) => out(json!({"verdict": match code { 2 => "bounty", 1 => "floor", _ => "nothing" },
                                        "code": code, "mu": mu})),
        None => out(json!({"verdict": "not_sent", "why": "the rule did not cross, or was refuted at home"})),
    }
}
