#!/usr/bin/env python3
"""Adjudicate the two v1.1 model labelings into one reviewed catalog.

Base = kimi-k2p6 (leaner, better-calibrated). deepseek-v4-pro is the second
opinion. The rules below encode the editorial judgment from a full human(Claude)
read of all 414 verses with both label sets side by side:

  - suicidal-ideation: keep only on genuine bodily-death/mortality verses;
    drop from the many "evil-doer -> hell" moral verses both models over-sprayed.
  - fresh-grief: keep on death + impermanence-of-life verses.
  - acute-shame/self-blame: keep only where the verse attributes fault to the
    listener; drop from empowerment / self-mastery verses (kimi over-added).
  - abuse-disclosure/victim/rage: keep where text has abuse/harm/enemy content.
  - despair/panic: keep when both models agree, or text corroborates.
  - tone: kimi base; soften kimi stern/warning when no harsh markers; harden to
    stern when kimi softened a genuinely harsh verse.
  - crisis themes (death/ascetic-discipline/moral-rebuke) injected where either
    model tagged them and the text corroborates.

A candidate label is only ever KEPT if at least one model proposed it
(content-gated union); nothing is invented. vulnerableStatesToAvoid is
recomputed as avoidWhen ∩ crisis-adjacent set.

Output: outputs/catalog.labeled.v1.1.adjudicated.json (then validate.py).
"""
from __future__ import annotations
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

CRISIS7 = {"acute-shame", "panic", "despair", "self-blame",
           "abuse-disclosure", "fresh-grief", "suicidal-ideation"}
HARSH_TONES = {"stern", "warning"}
CRISIS_THEMES = ("death", "ascetic-discipline", "moral-rebuke")
AV_ORDER = ["acute-shame", "panic", "despair", "self-blame", "abuse-disclosure",
            "fresh-grief", "suicidal-ideation", "rage-at-aggressor",
            "victim-of-relational-harm"]


def has(text, words):
    return any(w in text for w in words)


# marker sets (matched as lowercase substrings)
SUICIDE_OK = ("death", "die", "dies", "dying", "dead", "corpse", "bones",
              "grave", "funeral", "carries off", "carried off", "carry off",
              "seized", "messengers of death", "king of death",
              "lord of the departed", "slain", "lie on the earth",
              "useless log", "heap of corruption", "body is wasted",
              "body is destroyed", "white bones", "sear leaf")
GRIEF_OK = SUICIDE_OK + ("perish", "perishes", "all created things",
                         "come to an end", "comes to an end", "grief", "mourn",
                         "mourns", "no more", "beloved", "loss")
DESPAIR_OK = ("suffer", "suffers", "suffering", "hell", "evil path", "evil way",
              "evil deeds", "downward", "destroy", "destroys", "destruction",
              "torment", "burn", "burning", "bitter fruit", "ruin", "perish",
              "again and again", "grief")
PANIC_OK = ("flood", "fire", "iron ball", "lightning", "sudden", "carries off",
            "destroyed", "cleaves his head", "accusation")
BLAME_OK = ("evil", "sin", "sins", "fault", "faults", "guilt", "repent",
            "repents", "transgress", "transgressor", "wicked", "shame",
            "shameless", "misdeed", "ill-conditioned", "impure", "impurity",
            "taint", "vice", "vicious", "offend", "offence", "his own",
            "destroys himself", "his own enemy", "own works", "own deeds",
            "own misdeeds", "unrestrained", "sloth", "slothful", "lazy", "idle",
            "ought to be ashamed", "wretched")
ABUSE_OK = ("abuse", "abused", "beat", "robbed", "struck", "strike", "strikes",
            "flies at", "aggressor", "killed", "violence", "injure", "injures",
            "insult", "slaughter")
HARM_OK = ABUSE_OK + ("enemy", "hatred", "hate", "hates", "anger", "angry",
                      "quarrel", "blame", "blames", "wrong", "ill-natured",
                      "fault-finders", "reproof", "reproach", "hurt")
HARSH_OK = ("hell", "evil-doer", "evil deed", "evil deeds", "suffer", "suffers",
            "suffering", "perish", "destroy", "destruction", "go to hell",
            "evil path", "evil way", "burn", "torment", "iron ball", "death",
            "die", "slain", "bitter fruit", "wicked", "ill-conditioned", "sin")
ASCETIC_OK = ("ascetic", "penance", "fasting", "naked", "vow", "vows",
              "platted hair", "goat-skin", "emaciated", "tonsure", "yellow gown",
              "yellow dress", "dirt", "empty this boat", "lives alone in the forest")


def keep_state(s, text, in_both):
    if s == "acute-shame" or s == "self-blame":
        return has(text, BLAME_OK)
    if s == "despair":
        return in_both or has(text, DESPAIR_OK)
    if s == "panic":
        return in_both or has(text, PANIC_OK)
    if s == "fresh-grief":
        return has(text, GRIEF_OK)
    if s == "suicidal-ideation":
        return has(text, SUICIDE_OK)
    if s == "abuse-disclosure":
        return has(text, ABUSE_OK)
    if s in ("rage-at-aggressor", "victim-of-relational-harm"):
        return has(text, HARM_OK)
    return False


def adjudicate_tone(dt, kt, text):
    harsh = has(text, HARSH_OK)
    if kt in HARSH_TONES and dt not in HARSH_TONES and not harsh:
        return dt          # kimi over-toned a calm verse -> soften
    if dt in HARSH_TONES and kt not in HARSH_TONES and harsh:
        return dt          # kimi softened a genuinely harsh verse -> harden
    return kt


def adjudicate_themes(dth, kth, text):
    out = list(kth)
    for ct in CRISIS_THEMES:
        if ct in out:
            continue
        if ct not in dth and ct not in kth:
            continue
        if ct == "death":
            corrob = has(text, GRIEF_OK)
        elif ct == "ascetic-discipline":
            corrob = has(text, ASCETIC_OK)
        else:  # moral-rebuke
            corrob = has(text, BLAME_OK + ("hell", "rebuke", "reproof",
                                           "admonish", "evil-doer"))
        if not corrob:
            continue
        if len(out) < 4:
            out.append(ct)
        else:
            # drop a trailing non-crisis theme to make room
            for i in range(len(out) - 1, -1, -1):
                if out[i] not in CRISIS_THEMES:
                    out[i] = ct
                    break
    return out


def main():
    # read the committed v1.1 model outputs (reproducible from version control)
    LAB = os.path.join(HERE, "..", "labeled")
    D = {r["id"]: r for r in json.load(open(os.path.join(
        LAB, "catalog.labeled.v1.1.deepseek-v4-pro.json")))["rows"]}
    kdata = json.load(open(os.path.join(LAB, "catalog.labeled.v1.1.kimi-k2p6.json")))
    rows = []
    for kr in kdata["rows"]:
        i = kr["id"]
        dr = D.get(i, kr)
        text = kr["text"].lower()
        du, ku = set(dr["avoidWhen"]), set(kr["avoidWhen"])
        union = du | ku
        final_av = [s for s in AV_ORDER
                    if s in union and keep_state(s, text, s in du and s in ku)]
        vsta = [s for s in final_av if s in CRISIS7]
        row = dict(kr)
        row["tone"] = adjudicate_tone(dr["tone"], kr["tone"], text)
        row["themes"] = adjudicate_themes(dr["themes"], kr["themes"], text)
        row["avoidWhen"] = final_av
        row["vulnerableStatesToAvoid"] = vsta
        row["excludeOnCrisis"] = False
        row["labeledBy"] = "fireworks/kimi-k2p6+deepseek-v4-pro (v1.1, claude-adjudicated)"
        row["reviewedBy"] = "claude-opus-4.8 (adjudicated kimi-k2p6 base + deepseek-v4-pro, v1.1)"
        rows.append(row)
    out = {"labeledAt": kdata.get("labeledAt"), "provider": "adjudicated",
           "model": "kimi-k2p6-base+deepseek-v4-pro", "promptVersion": "labeling-v1.1",
           "grouping": kdata.get("grouping"), "rowCount": len(rows), "rows": rows}
    op = os.path.join(LAB, "catalog.labeled.v1.1.adjudicated.json")
    json.dump(out, open(op, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print("wrote", op, "with", len(rows), "rows")


if __name__ == "__main__":
    main()
