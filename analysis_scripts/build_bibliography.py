#!/usr/bin/env python3
"""Generate references.bib from the curated literature review.

Every field comes from the review spreadsheet. Nothing is inferred: a work with
no recorded DOI simply has no DOI field. Entry keys are stable so that the
drafts can cite them before the bibliography is finalised.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

PAPER = Path(__file__).resolve().parents[1]
ROOT = PAPER.parents[1]
CSV = ROOT / "research/docs/literature/MV_ZSAD_LITERATURE_REVIEW.csv"
OUT = PAPER / "references.bib"

KEY = {
    "1": "kim2026viewfusion", "2": "hou2026visualad", "3": "jeong2023winclip",
    "4": "zhou2024anomalyclip", "5": "li2024promptad", "6": "cao2024adaclip",
    "7": "ma2025aaclip", "8": "fe2025clip", "9": "rare2025clip",
    "10": "moe2026clip", "11": "fead2026", "12": "dycclip2026",
    "13": "dssp2026", "14": "papl2026", "15": "oneforall2026",
    "16": "wang2024realiad", "17": "zhu2026realiadvariety", "18": "he2024mvas",
    "19": "idif2025", "20": "multiflow2025", "21": "epipolar2025",
    "22": "viewsense2026", "23": "glad2026", "24": "manta2025",
    "25": "m2ad2026", "26": "survey2025", "27": "anocalib2026",
    "28": "anomalyvfm2026",
    # Score-level fusion, multi-view learning and multiple-instance learning.
    # Added 2026-09-26 so that the paper is positioned against the fusion
    # literature rather than only against anomaly detection.
    "29": "kittler1998combining", "30": "kuncheva2002six",
    "31": "jain2005score", "32": "snoek2005early",
    "33": "xu2013mvsurvey", "34": "zhao2017mvoverview",
    "35": "su2015mvcnn", "36": "dietterich1997mil",
    "37": "ilse2018attention", "38": "carbonneau2018mil",
    "39": "david2003order",
}

JOURNALS = ("Pattern Recognition", "Artificial Intelligence Review",
            "IEEE Transactions on Multimedia")

# Source-verified bibliographic fields.  These overrides contain publication
# metadata only; they do not change the curated review notes or citation keys.
# Sources: publisher DOI records and official conference proceedings, audited
# 2026-09-24.  Article numbers are stored in `pages` because the Elsevier
# numeric BibTeX style renders that field reliably.
VERIFIED = {
    "kim2026viewfusion": dict(kind="inproceedings",
        booktitle="2026 International Conference on Electronics, Information, and Communication (ICEIC)",
        pages="1--6", doi="10.1109/ICEIC69189.2026.11386302"),
    "hou2026visualad": dict(kind="inproceedings",
        booktitle="Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)",
        pages="21346--21356"),
    "jeong2023winclip": dict(kind="inproceedings",
        booktitle="Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)",
        pages="19606--19616"),
    "zhou2024anomalyclip": dict(kind="inproceedings",
        booktitle="The Twelfth International Conference on Learning Representations (ICLR)"),
    "li2024promptad": dict(kind="inproceedings",
        booktitle="Proceedings of the IEEE/CVF Winter Conference on Applications of Computer Vision (WACV)",
        pages="1093--1102"),
    "cao2024adaclip": dict(kind="inproceedings",
        booktitle="Computer Vision -- ECCV 2024", pages="55--72",
        doi="10.1007/978-3-031-72761-0_4"),
    "ma2025aaclip": dict(kind="inproceedings",
        booktitle="Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)",
        pages="4744--4754"),
    "fe2025clip": dict(kind="inproceedings",
        booktitle="Proceedings of the IEEE/CVF International Conference on Computer Vision (ICCV)",
        pages="21220--21230"),
    "rare2025clip": dict(kind="inproceedings",
        booktitle="Proceedings of the IEEE/CVF International Conference on Computer Vision (ICCV)",
        pages="24478--24487"),
    "moe2026clip": dict(kind="inproceedings",
        booktitle="Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)",
        pages="35534--35544"),
    "fead2026": dict(kind="article", journal="Pattern Recognition",
        volume="180", pages="114356", doi="10.1016/j.patcog.2026.114356"),
    "dycclip2026": dict(kind="article", journal="Pattern Recognition",
        volume="176", pages="113215", doi="10.1016/j.patcog.2026.113215"),
    "dssp2026": dict(kind="article", journal="Pattern Recognition",
        volume="180", pages="114002", doi="10.1016/j.patcog.2026.114002"),
    "papl2026": dict(kind="article", journal="Pattern Recognition",
        volume="178", pages="113489", doi="10.1016/j.patcog.2026.113489"),
    "oneforall2026": dict(kind="article", journal="Pattern Recognition",
        volume="180", pages="114123", doi="10.1016/j.patcog.2026.114123"),
    "wang2024realiad": dict(kind="inproceedings",
        booktitle="Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)",
        pages="22883--22892"),
    "zhu2026realiadvariety": dict(kind="article", journal="Pattern Recognition",
        volume="178", pages="113354", doi="10.1016/j.patcog.2026.113354"),
    "he2024mvas": dict(kind="article", year="2026",
        journal="IEEE Transactions on Multimedia", volume="28",
        pages="4485--4496", doi="10.1109/TMM.2026.3660076"),
    "idif2025": dict(kind="article",
        journal="Proceedings of the AAAI Conference on Artificial Intelligence",
        volume="39", number="12", pages="12381--12389",
        doi="10.1609/aaai.v39i12.33349"),
    "multiflow2025": dict(kind="inproceedings",
        booktitle="Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition Workshops (CVPRW)",
        pages="3972--3983"),
    "viewsense2026": dict(kind="article",
        journal="Proceedings of the AAAI Conference on Artificial Intelligence",
        volume="40", number="4", pages="3065--3073",
        doi="10.1609/aaai.v40i4.37299"),
    "manta2025": dict(kind="inproceedings",
        booktitle="Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)",
        pages="25518--25527"),
    "m2ad2026": dict(kind="article", journal="Pattern Recognition",
        volume="179", pages="113666", doi="10.1016/j.patcog.2026.113666"),
    "survey2025": dict(kind="article",
        author="Zhuo Li and Yuhao Yan and Xiangheng Wang and Yifei Ge and Lin Meng",
        journal="Artificial Intelligence Review", volume="58", number="9",
        pages="279", doi="10.1007/s10462-025-11287-7"),
    "anocalib2026": dict(kind="article", year="2027",
        journal="Pattern Recognition", volume="183", pages="114810",
        doi="10.1016/j.patcog.2026.114810"),
    "anomalyvfm2026": dict(kind="inproceedings",
        booktitle="Proceedings of the IEEE/CVF Conference on Computer Vision and Pattern Recognition (CVPR)",
        pages="35555--35566"),
    "kittler1998combining": dict(kind="article",
        journal="IEEE Transactions on Pattern Analysis and Machine Intelligence",
        volume="20", number="3", pages="226--239", doi="10.1109/34.667881"),
    "kuncheva2002six": dict(kind="article",
        journal="IEEE Transactions on Pattern Analysis and Machine Intelligence",
        volume="24", number="2", pages="281--286", doi="10.1109/34.982906"),
    "jain2005score": dict(kind="article", journal="Pattern Recognition",
        volume="38", number="12", pages="2270--2285",
        doi="10.1016/j.patcog.2005.01.012"),
    "snoek2005early": dict(kind="inproceedings",
        booktitle="Proceedings of the 13th ACM International Conference on Multimedia",
        pages="399--402", doi="10.1145/1101149.1101236"),
    "xu2013mvsurvey": dict(kind="misc",
        howpublished="arXiv preprint arXiv:1304.5634"),
    "zhao2017mvoverview": dict(kind="article", journal="Information Fusion",
        volume="38", pages="43--54", doi="10.1016/j.inffus.2017.02.007"),
    "su2015mvcnn": dict(kind="inproceedings",
        booktitle="Proceedings of the IEEE International Conference on Computer Vision (ICCV)",
        pages="945--953", doi="10.1109/ICCV.2015.114"),
    "dietterich1997mil": dict(kind="article", journal="Artificial Intelligence",
        volume="89", number="1-2", pages="31--71",
        doi="10.1016/S0004-3702(96)00034-3"),
    "ilse2018attention": dict(kind="inproceedings",
        booktitle="Proceedings of the 35th International Conference on Machine Learning (ICML)",
        volume="80", pages="2127--2136"),
    "carbonneau2018mil": dict(kind="article", journal="Pattern Recognition",
        volume="77", pages="329--353", doi="10.1016/j.patcog.2017.10.009"),
    "david2003order": dict(kind="book", publisher="John Wiley and Sons",
        edition="3rd", doi="10.1002/0471722162"),
}


def escape(text: str) -> str:
    return text.replace("&", r"\&").replace("%", r"\%").replace("_", r"\_")


# Proper names that must keep their capital even though they are plain words.
PROPER = {"Variety"}


def _needs_braces(token: str) -> bool:
    core = token.strip(":,.;?!()")
    if core in PROPER:
        return True
    for part in core.replace("/", "-").split("-"):
        letters = [c for c in part if c.isalpha()]
        if len(letters) >= 2 and all(c.isupper() for c in letters):
            return True          # acronym: CLIP, IAD, ZSAD, ONE
        if any(c.isupper() for c in part[1:]):
            return True          # camel case: WinCLIP, VisualAD, MoECLIP
    return False


def protect_title(text: str) -> str:
    """Brace acronyms and camel-case names so the numeric Elsevier style,
    which sentence-cases titles, does not print WinCLIP as "Winclip"."""
    out = []
    for token in text.split(" "):
        if _needs_braces(token):
            head = len(token) - len(token.lstrip("("))
            tail = len(token) - len(token.rstrip(":,.;?!)"))
            core = token[head:len(token) - tail]
            token = token[:head] + "{" + core + "}" + token[len(token) - tail:]
        out.append(token)
    return " ".join(out)


def arxiv_note(url: str, venue: str) -> str:
    """'arXiv preprint arXiv:2503.11088' instead of 'arXiv 2025', which the
    style otherwise prints next to the year as 'arXiv 2025, 2025'."""
    tail = url.rstrip("/").rsplit("/", 1)[-1]
    return f"arXiv preprint arXiv:{tail}" if "arxiv.org" in url else venue


def authors(field: str) -> str:
    return " and ".join(a.strip() for a in field.split(";") if a.strip())


def main():
    rows = list(csv.DictReader(CSV.open(encoding="utf-8")))
    entries = []
    for r in rows:
        key = KEY[r["id"]]
        verified = VERIFIED.get(key)
        if verified:
            kind = verified["kind"]
            fields = [
                ("author", verified.get("author", authors(r["tac_gia"]))),
                ("title", protect_title(escape(r["ten_bai_bao"].strip()))),
                ("year", verified.get("year", r["nam"].strip())),
            ]
            for name in ("journal", "booktitle", "howpublished", "publisher",
                         "edition", "volume", "number", "pages", "doi"):
                if verified.get(name):
                    fields.append((name, verified[name]))
            url = r["paper_url"].strip() or r["doi_or_publisher_url"].strip()
            if url:
                fields.append(("url", url))
            body = ",\n".join(f"  {k} = {{{v}}}" for k, v in fields if v)
            entries.append(f"@{kind}{{{key},\n{body}\n}}")
            continue
        venue = r["venue"].strip()
        journal = next((j for j in JOURNALS if venue.startswith(j)), None)
        fields = [("author", authors(r["tac_gia"])),
                  ("title", protect_title(escape(r["ten_bai_bao"].strip()))),
                  ("year", r["nam"].strip())]
        if journal:
            kind = "article"
            fields.append(("journal", journal))
            vol = re.sub(rf"^{re.escape(journal)}[, ]*", "", venue).strip()
            if vol:
                fields.append(("note", escape(vol)))
        elif venue.lower().startswith("arxiv"):
            kind = "misc"
            fields.append(("howpublished", escape(arxiv_note(r["paper_url"].strip(), venue))))
        else:
            kind = "inproceedings"
            fields.append(("booktitle", escape(venue)))
        doi = r["doi_or_publisher_url"].strip()
        if doi.startswith("https://doi.org/"):
            fields.append(("doi", doi[len("https://doi.org/"):]))
        url = r["paper_url"].strip() or doi
        if url:
            fields.append(("url", url))
        body = ",\n".join(f"  {k} = {{{v}}}" for k, v in fields if v)
        entries.append(f"@{kind}{{{key},\n{body}\n}}")

    OUT.write_text("% Generated by scripts/build_bibliography.py from the\n"
                   "% curated literature review. Do not edit by hand.\n\n"
                   + "\n\n".join(entries) + "\n", encoding="utf-8")
    print(f"wrote {OUT.name}: {len(entries)} entries")
    for r in rows:
        print(f"  {KEY[r['id']]:24s} {r['nam']}  {r['ten_bai_bao'][:58]}")


if __name__ == "__main__":
    main()
