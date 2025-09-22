# data_processor.py
import os
import json
import re
from typing import List, Tuple, Dict, Any
from config import DATA_DIR, CHUNK_SIZE, CHUNK_OVERLAP

def _normalize_whitespace(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()

class DataProcessor:
    """
    Produces high-quality, structured chunks from each JSON match:
    - match_header, match_summary, innings_summary, over, delivery
    - special chunks for finals/semi/finals_stage, player_aggregates
    - raw_json windows for completeness
    - generates deterministic chunk ids and metadata for citation
    """
    def __init__(self):
        self.matches_data: List[Tuple[str, Dict[str, Any]]] = []
        self.chunks: List[str] = []
        self.metadata: List[dict] = []
        self.global_stats: Dict[str, Any] = {}

    def load_json_files(self):
        print(f"Looking for JSON in: {DATA_DIR}")
        files = []
        if os.path.exists(DATA_DIR):
            files = [f for f in os.listdir(DATA_DIR) if f.endswith(".json")]
            files = sorted(files)
        print(f"Found {len(files)} JSON files")
        for filename in files:
            path = os.path.join(DATA_DIR, filename)
            try:
                with open(path, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                self.matches_data.append((filename, data))
            except Exception as e:
                print(f"Failed to load {filename}: {e}")

    def _append_chunk(self, text: str, meta: Dict[str, Any]):
        if not text:
            return
        content = _normalize_whitespace(text)
        meta_copy = dict(meta)
        meta_copy["content"] = content
        meta_copy["global_chunk_id"] = len(self.metadata) + 1
        self.chunks.append(content)
        self.metadata.append(meta_copy)

    def _extract_info(self, filename: str, data: Dict[str, Any]) -> Dict[str,Any]:
        info = data.get("info", {}) or {}
        teams = info.get("teams", [])
        dates = info.get("dates", [""])
        date = dates[0] if isinstance(dates, list) and dates else (info.get("date") or "")
        venue = info.get("venue") or info.get("location") or ""
        event = info.get("event") or {}
        tournament = event.get("name") if isinstance(event, dict) else info.get("tournament", "")
        stage = event.get("stage") if isinstance(event, dict) else info.get("stage", "")
        match_type = info.get("match_type") or ""
        player_of_match = info.get("player_of_match") or []
        outcome = info.get("outcome") or {}
        winner = outcome.get("winner") or ""
        season = info.get("season") or ""
        year = date[:4] if date else ""
        return {
            "teams": teams, "date": date, "venue": venue, "tournament": tournament,
            "stage": stage, "match_type": match_type, "player_of_match": player_of_match,
            "winner": winner, "season": season, "year": year
        }

    def _match_header(self, filename, data) -> Tuple[str, dict]:
        info = self._extract_info(filename, data)
        parts = [f"MATCH FILE: {filename}"]
        if info["tournament"]:
            parts.append(f"TOURNAMENT: {info['tournament']}")
        if info["teams"]:
            parts.append("TEAMS: " + " vs ".join(info["teams"]))
        if info["date"]:
            parts.append(f"DATE: {info['date']}")
        if info["venue"]:
            parts.append(f"VENUE: {info['venue']}")
        if info["stage"]:
            parts.append(f"STAGE: {info['stage']}")
        header_text = "\n".join(parts)
        meta = {"source_file": filename, "chunk_type":"match_header", **info}
        return header_text, meta

    def _innings_summary(self, filename, inn_idx, inn_data) -> Tuple[str, dict]:
        team = inn_data.get("team") or inn_data.get("batting_team") or ""
        total_runs = 0; total_wickets = 0; total_overs = 0
        fours = sixes = 0
        batter_runs = {}
        bowler_stats = {}
        overs = inn_data.get("overs", [])
        for over in overs:
            # over entries may have "over" and "deliveries"
            total_overs += 1
            for delivery in over.get("deliveries", []):
                runs = delivery.get("runs", {}).get("total", 0)
                total_runs += runs
                if runs == 4: fours += 1
                if runs == 6: sixes += 1
                batter = delivery.get("batter") or delivery.get("batsman") or ""
                bowler = delivery.get("bowler") or ""
                if batter:
                    batter_runs[batter] = batter_runs.get(batter,0) + runs
                if bowler:
                    if bowler not in bowler_stats:
                        bowler_stats[bowler] = {"runs":0,"wickets":0}
                    bowler_stats[bowler]["runs"] += runs
                    if "wickets" in delivery and delivery["wickets"]:
                        bowler_stats[bowler]["wickets"] += len(delivery["wickets"])
                        total_wickets += len(delivery["wickets"])
                    else:
                        w = delivery.get("wicket") or delivery.get("dismissal") or {}
                        if isinstance(w, dict) and w:
                            bowler_stats[bowler]["wickets"] += 1
                            total_wickets += 1
        parts = [f"INNINGS {inn_idx}: {team}", f"SCORE: {total_runs} runs for {total_wickets} wickets (approx {total_overs} overs)",
                 f"BOUNDARIES: {fours} fours and {sixes} sixes"]
        if batter_runs:
            top_batters = sorted(batter_runs.items(), key=lambda x: x[1], reverse=True)[:6]
            parts.append("TOP BATTERS: " + ", ".join([f"{n} {r}r" for n,r in top_batters]))
        if bowler_stats:
            top_bowlers = sorted([(b,s["wickets"], s["runs"]) for b,s in bowler_stats.items()], key=lambda x: x[1], reverse=True)[:6]
            parts.append("TOP BOWLERS: " + ", ".join([f"{n} {w}w/{r}r" for n,w,r in top_bowlers]))
        text = "\n".join(parts)
        meta = {"source_file": filename, "chunk_type":"innings_summary", "innings": inn_idx, "team": team}
        return text, meta

    def _over_text(self, filename, inn_idx, over_obj):
        over_num = over_obj.get("over") or over_obj.get("over_number") or ""
        parts = [f"OVER {over_num} (Innings {inn_idx}):"]
        for delivery in over_obj.get("deliveries", []):
            batter = delivery.get("batter") or delivery.get("batsman") or ""
            bowler = delivery.get("bowler") or ""
            runs = delivery.get("runs", {}).get("total", "")
            wicket_text = ""
            if "wickets" in delivery and delivery["wickets"]:
                wparts = []
                for w in delivery["wickets"]:
                    p = w.get("player_out") or w.get("player") or ""
                    kind = w.get("kind") or ""
                    wparts.append(f"{p} ({kind})" if p else kind)
                wicket_text = " WICKET: " + ", ".join([x for x in wparts if x])
            elif delivery.get("wicket") or delivery.get("dismissal"):
                info = delivery.get("wicket") or delivery.get("dismissal")
                if isinstance(info, dict):
                    p = info.get("player_out") or info.get("player") or ""
                    kind = info.get("kind") or ""
                    if p or kind:
                        wicket_text = f" WICKET: {p} ({kind})"
            parts.append(f"{bowler} -> {batter} : {runs}{wicket_text}")
        text = "\n".join(parts)
        meta = {"source_file": filename, "chunk_type":"over", "innings":inn_idx, "over": over_num}
        return text, meta

    def _delivery_text(self, filename, inn_idx, over_num, d_idx, delivery):
        batter = delivery.get("batter") or delivery.get("batsman") or ""
        bowler = delivery.get("bowler") or ""
        runs = delivery.get("runs", {}).get("total", 0)
        extras = delivery.get("runs", {})
        extras_total = 0
        if isinstance(extras, dict):
            extras_total = sum(v for k,v in extras.items() if k!="total" and isinstance(v,int))
        wicket_descr = ""
        if "wickets" in delivery and delivery["wickets"]:
            parts = []
            for w in delivery["wickets"]:
                p = w.get("player_out") or w.get("player") or ""
                kind = w.get("kind") or ""
                if p:
                    parts.append(f"{p} ({kind})" if kind else p)
                elif kind:
                    parts.append(kind)
            if parts:
                wicket_descr = " WICKET: " + ", ".join(parts)
        elif delivery.get("wicket") or delivery.get("dismissal"):
            w = delivery.get("wicket") or delivery.get("dismissal")
            if isinstance(w, dict) and w:
                p = w.get("player_out") or w.get("player") or ""
                kind = w.get("kind") or ""
                wicket_descr = f" WICKET: {p} ({kind})" if p or kind else ""
        desc = f"DELIVERY: Inn{inn_idx} Over{over_num} Ball{d_idx} — {bowler} to {batter} : {runs} runs{' extras:'+str(extras_total) if extras_total else ''}{wicket_descr}"
        meta = {"source_file": filename, "chunk_type":"delivery", "innings":inn_idx, "over":over_num, "delivery_index":d_idx}
        return desc, meta

    def _raw_json_windows(self, filename, data, window_chars=1600, step=800):
        s = json.dumps(data, ensure_ascii=False)
        s = _normalize_whitespace(s)
        out = []
        i = 0; idx = 1
        while i < len(s):
            chunk = s[i:i+window_chars]
            meta = {"source_file": filename, "chunk_type":"raw_json", "raw_window_index": idx}
            out.append((chunk, meta))
            idx += 1
            if i + window_chars >= len(s):
                break
            i += step
        return out

    def _build_full_text(self, filename, data):
        parts = []
        header, _ = self._match_header(filename, data)
        parts.append(header)
        innings = data.get("innings", []) or []
        for idx, inn in enumerate(innings, start=1):
            if isinstance(inn, dict) and len(inn)==1:
                inn = list(inn.values())[0]
            s_text, _ = self._innings_summary(filename, idx, inn)
            parts.append(s_text)
            cnt = 0
            for over in inn.get("overs", []):
                for delivery in over.get("deliveries", []):
                    cnt += 1
                    d_text, _ = self._delivery_text(filename, idx, over.get("over"), cnt, delivery)
                    parts.append(d_text)
                    if cnt >= 120:  # limit deliveries for full-text to avoid extreme length
                        break
                if cnt >= 120:
                    break
        info = data.get("info", {}) or {}
        outcome = info.get("outcome") or {}
        if outcome:
            w = outcome.get("winner") or ""
            if w:
                parts.append(f"RESULT: {w}")
        commentary = data.get("commentary") or data.get("notes") or ""
        if commentary:
            parts.append(_normalize_whitespace(commentary if isinstance(commentary,str) else json.dumps(commentary)))
        return _normalize_whitespace("\n\n".join(parts))

    def _split_with_overlap(self, text: str, size:int, overlap:int):
        text = _normalize_whitespace(text)
        if not text:
            return []
        if len(text) <= size:
            return [text]
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + size, len(text))
            chunks.append(text[start:end])
            if end == len(text):
                break
            start = end - overlap if (end - overlap) > start else end
        return chunks

    def create_chunks(self):
        print("Creating chunks from matches...")
        for filename, data in self.matches_data:
            try:
                info = self._extract_info(filename, data)
                # header
                h_text, h_meta = self._match_header(filename, data)
                self._append_chunk(h_text, h_meta)

                # add match summary chunk (explicit)
                summary_lines = [h_text]
                # if outcome exists add outcome
                outcome = data.get("info", {}).get("outcome") or {}
                if outcome:
                    w = outcome.get("winner") or ""
                    by = outcome.get("by") or {}
                    if w:
                        if isinstance(by, dict):
                            if by.get("runs"):
                                summary_lines.append(f"Winner: {w} by {by.get('runs')} runs")
                            elif by.get("wickets"):
                                summary_lines.append(f"Winner: {w} by {by.get('wickets')} wickets")
                            else:
                                summary_lines.append(f"Winner: {w}")
                        else:
                            summary_lines.append(f"Winner: {w}")
                # player_of_match
                pom = data.get("info", {}).get("player_of_match") or []
                if pom:
                    summary_lines.append("Player(s) of match: " + ", ".join(pom))
                summary_text = "\n".join(summary_lines)
                self._append_chunk(summary_text, {"source_file": filename, "chunk_type":"match_summary", **info})

                # innings/overs/delivery chunks
                innings_list = data.get("innings", []) or []
                match_batter_stats = {}
                match_bowler_stats = {}

                for inn_idx, inn in enumerate(innings_list, start=1):
                    if isinstance(inn, dict) and len(inn) == 1:
                        inn = list(inn.values())[0]
                    # innings summary
                    try:
                        s_text, s_meta = self._innings_summary(filename, inn_idx, inn)
                        self._append_chunk(s_text, s_meta)
                    except Exception:
                        pass

                    # overs and deliveries
                    for over_obj in inn.get("overs", []):
                        try:
                            o_text, o_meta = self._over_text(filename, inn_idx, over_obj)
                            self._append_chunk(o_text, o_meta)
                        except Exception:
                            pass
                        for d_idx, delivery in enumerate(over_obj.get("deliveries", []), start=1):
                            try:
                                d_text, d_meta = self._delivery_text(filename, inn_idx, over_obj.get("over"), d_idx, delivery)
                                self._append_chunk(d_text, d_meta)
                            except Exception:
                                pass

                            # accumulate per-batter and bowler stats
                            runs = delivery.get("runs", {}).get("total", 0)
                            batter = delivery.get("batter") or delivery.get("batsman") or ""
                            bowler = delivery.get("bowler") or ""
                            if batter:
                                bs = match_batter_stats.setdefault(batter, {"runs":0,"fours":0,"sixes":0})
                                bs["runs"] += delivery.get("runs", {}).get("batter", runs) if isinstance(delivery.get("runs", {}), dict) else runs
                                if runs == 4: bs["fours"] += 1
                                if runs == 6: bs["sixes"] += 1
                            if bowler:
                                bw = match_bowler_stats.setdefault(bowler, {"runs_conceded":0,"wickets":0})
                                bw["runs_conceded"] += runs
                                if "wickets" in delivery and delivery["wickets"]:
                                    bw["wickets"] += len(delivery["wickets"])
                                else:
                                    wi = delivery.get("wicket") or delivery.get("dismissal") or {}
                                    if isinstance(wi, dict) and wi:
                                        bw["wickets"] += 1

                # store per-match aggregates
                if match_batter_stats:
                    lines = [f"MATCH BATTER STATS ({filename}):"]
                    for p, stats in sorted(match_batter_stats.items(), key=lambda x: x[1]["runs"], reverse=True):
                        lines.append(f"{p}: {stats['runs']} runs, {stats['fours']} fours, {stats['sixes']} sixes")
                    self._append_chunk("\n".join(lines), {"source_file": filename, "chunk_type":"match_batter_stats", **info})

                if match_bowler_stats:
                    lines = [f"MATCH BOWLER STATS ({filename}):"]
                    for p, stats in sorted(match_bowler_stats.items(), key=lambda x: x[1]["wickets"], reverse=True):
                        lines.append(f"{p}: {stats['wickets']} wickets, {stats['runs_conceded']} runs conceded")
                    self._append_chunk("\n".join(lines), {"source_file": filename, "chunk_type":"match_bowler_stats", **info})

                # sliding windows for deliveries
                try:
                    sliding = self._sliding_delivery_windows(filename, innings_list, window_deliveries=40, step_deliveries=15)
                    for txt, meta in sliding:
                        self._append_chunk(txt, meta)
                except Exception:
                    pass

                # raw JSON windows
                try:
                    raw_windows = self._raw_json_windows(filename, data, window_chars=1600, step=800)
                    for txt, meta in raw_windows:
                        self._append_chunk(txt, meta)
                except Exception:
                    pass

                # full text windows split with overlap
                full_text = self._build_full_text(filename, data)
                windows = self._split_with_overlap(full_text, CHUNK_SIZE, CHUNK_OVERLAP)
                for idx, w in enumerate(windows, start=1):
                    meta = {"source_file": filename, "chunk_type":"window", "chunk_id": idx, **info}
                    self._append_chunk(w, meta)

            except Exception as e:
                print(f"Error processing {filename}: {e}")

        print(f"Created {len(self.chunks)} chunks from {len(self.matches_data)} files")
        self.compute_global_stats()

    def _sliding_delivery_windows(self, filename, innings_list, window_deliveries=40, step_deliveries=15):
        # flatten deliveries
        deliveries = []
        mapping = []
        for inn_idx, inn in enumerate(innings_list, start=1):
            if isinstance(inn, dict) and len(inn) == 1:
                inn = list(inn.values())[0]
            for over in inn.get("overs", []):
                over_num = over.get("over")
                for d_idx, d in enumerate(over.get("deliveries", []), start=1):
                    deliveries.append(d)
                    mapping.append((inn_idx, over_num, d_idx))
        out = []
        total = len(deliveries)
        start = 0; win = 1
        while start < total:
            end = min(start + window_deliveries, total)
            pieces = []
            for i in range(start, end):
                inn_idx, over_num, d_idx = mapping[i]
                d = deliveries[i]
                batter = d.get("batter") or d.get("batsman") or ""
                bowler = d.get("bowler") or ""
                runs = d.get("runs", {}).get("total", 0)
                pieces.append(f"Inn{inn_idx} O{over_num} D{d_idx}: {bowler}->{batter} {runs}")
            text = " | ".join(pieces)
            meta = {"source_file": filename, "chunk_type":"sliding_deliveries", "window_id":win, "start_index": start+1, "end_index": end}
            out.append((text, meta))
            win += 1
            if end == total:
                break
            start += step_deliveries
        return out

    def compute_global_stats(self):
        print("Computing global stats across all matches...")
        finals = []; semis = []
        runs_by_player = {}; wickets_by_bowler = {}
        player_of_series = {}

        for filename, data in self.matches_data:
            info = data.get("info", {}) or {}
            event = info.get("event") or {}
            stage = event.get("stage") if isinstance(event, dict) else info.get("stage", "")
            date = (info.get("dates") or [""])[0] if isinstance(info.get("dates"), list) else info.get("dates","")
            year = date[:4] if date else ""
            outcome = info.get("outcome") or {}
            winner = outcome.get("winner") or ""
            pom = info.get("player_of_match") or []
            if stage and "final" in str(stage).lower():
                finals.append({"year": year, "winner": winner, "teams": info.get("teams", []), "file": filename})
            if stage and "semi" in str(stage).lower():
                semis.append({"year": year, "winner": winner, "teams": info.get("teams", []), "file": filename})
            if "player_of_series" in info:
                player_of_series[year or filename] = info.get("player_of_series")

            for inn in data.get("innings", []):
                if isinstance(inn, dict) and len(inn) == 1:
                    inn = list(inn.values())[0]
                for over in inn.get("overs", []):
                    for delivery in over.get("deliveries", []):
                        runs = delivery.get("runs", {}).get("total", 0)
                        batter = delivery.get("batter") or delivery.get("batsman") or ""
                        bowler = delivery.get("bowler") or ""
                        if batter:
                            runs_by_player[batter] = runs_by_player.get(batter, 0) + (delivery.get("runs", {}).get("batter", runs) if isinstance(delivery.get("runs", {}), dict) else runs)
                        if "wickets" in delivery and delivery["wickets"]:
                            if bowler:
                                wickets_by_bowler[bowler] = wickets_by_bowler.get(bowler, 0) + len(delivery["wickets"])
                        else:
                            w = delivery.get("wicket") or delivery.get("dismissal") or {}
                            if isinstance(w, dict) and w:
                                if bowler:
                                    wickets_by_bowler[bowler] = wickets_by_bowler.get(bowler, 0) + 1

        def top_n(d, n=50):
            return sorted(d.items(), key=lambda x: x[1], reverse=True)[:n]

        stats = {
            "finals": finals,
            "semis": semis,
            "player_of_series": player_of_series,
            "top_run_scorers": top_n(runs_by_player, 200),
            "top_wicket_takers": top_n(wickets_by_bowler, 200),
            "runs_by_player_full": runs_by_player,
            "wickets_by_bowler_full": wickets_by_bowler
        }
        self.global_stats = stats
        out_path = os.path.join(DATA_DIR, "global_stats.json")
        try:
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=2, ensure_ascii=False)
            print(f"Saved global stats to {out_path}")
        except Exception as e:
            print(f"Failed to save global stats: {e}")

    def get_chunks(self):
        return self.chunks, self.metadata

if __name__ == "__main__":
    dp = DataProcessor()
    dp.load_json_files()
    dp.create_chunks()
    print("Chunks:", len(dp.chunks))
    print("Global stats keys:", list(dp.global_stats.keys()))
