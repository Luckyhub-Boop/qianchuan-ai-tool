from __future__ import annotations

import re
from collections import Counter
from typing import Any


# 常见虚词/功能字。用于从字符 n-gram 里过滤掉没有实义的组合。
STOP_CHARS = set(
    "的了是在我你他她它咱们家人们有和就不都一很也到说要去会着没"
    "好看自己这那这个那个然后因为所以如果但是而且还是或者"
    "吗呢吧啊呀哦哈啦嘛哪啥什么怎么多少几"
)

# 直播带货 + 教育课程里常见口头禅/引导语。
COMMON_CATCHPHRASES = (
    "对不对", "好不好", "对吧", "是不是", "是不是啊", "明白吗", "懂了吗",
    "记住了吗", "听懂了没有", "家人们", "宝贝们", "宝宝们", "各位家长",
    "扣个1", "扣1", "点亮灯牌", "点个关注", "点点赞", "下单", "去拍",
    "拍下来", "赶紧去拍", "点下方", "小黄车", "橱窗", "链接", "福利",
    "立减", "包邮", "仅限", "最后一波", "名额有限", "先到先得", "跟上",
)


def _only_chinese(text: str) -> str:
    return re.sub(r"[^\u4e00-\u9fff]", "", str(text or ""))


def _texts_by_speaker(transcript: dict[str, Any]) -> dict[str, list[str]]:
    segments = transcript.get("segments") if isinstance(transcript, dict) else []
    groups: dict[str, list[str]] = {}
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        text = str(segment.get("text") or "").strip()
        if not text:
            continue
        speaker = str(segment.get("speaker") or "_unassigned")
        groups.setdefault(speaker, []).append(text)
    return groups


def _frequent_ngrams(
    texts: list[str],
    min_len: int = 2,
    max_len: int = 4,
    min_count: int = 2,
    top_n: int = 30,
) -> list[dict[str, Any]]:
    counter: Counter[str] = Counter()
    for text in texts:
        clean = _only_chinese(text)
        for length in range(min_len, max_len + 1):
            for index in range(len(clean) - length + 1):
                gram = clean[index:index + length]
                if any(char in STOP_CHARS for char in gram):
                    continue
                counter[gram] += 1
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for gram, count in counter.most_common():
        if count < min_count:
            continue
        if any(gram in existing or existing in gram for existing in seen):
            continue
        items.append({"term": gram, "count": count})
        seen.add(gram)
        if len(items) >= top_n:
            break
    return items


def _catchphrases(texts: list[str], min_count: int = 2, top_n: int = 20) -> list[dict[str, Any]]:
    joined = "\n".join(texts)
    counter: Counter[str] = Counter()
    for phrase in COMMON_CATCHPHRASES:
        count = joined.count(phrase)
        if count >= min_count:
            counter[phrase] = count
    # 统计高频短句（3-6 字），作为自定义口头禅候选。
    for text in texts:
        clean = _only_chinese(text)
        for length in (3, 4):
            for index in range(len(clean) - length + 1):
                gram = clean[index:index + length]
                if gram in COMMON_CATCHPHRASES:
                    continue
                counter[gram] += 1
    items: list[dict[str, Any]] = []
    for phrase, count in counter.most_common():
        if count < min_count:
            continue
        items.append({"phrase": phrase, "count": count})
        if len(items) >= top_n:
            break
    return items


def _style_profile(texts: list[str], duration_seconds: float) -> dict[str, Any]:
    char_count = sum(len(_only_chinese(text)) for text in texts)
    chars_per_second = round(char_count / duration_seconds, 2) if duration_seconds > 0 else None
    segment_count = len(texts)
    avg_sentence_length = round(char_count / segment_count, 1) if segment_count else None
    question_count = sum(
        1 for text in texts if text.strip().endswith(("吗", "呢", "吧")) or "是不是" in text or "对不对" in text
    )
    command_count = sum(
        1 for text in texts
        if any(word in text for word in ("扣", "拍", "下单", "点击", "链接", "橱窗", "小黄车", "点个关注", "点亮灯牌"))
    )
    interjection_count = sum(
        len(re.findall(r"[啊呀哦呢吧啦哈]", text)) for text in texts
    )
    question_rate = round(question_count / segment_count, 3) if segment_count else None
    command_rate = round(command_count / segment_count, 3) if segment_count else None
    interjection_rate = round(interjection_count / char_count, 4) if char_count else None
    parts: list[str] = []
    if chars_per_second is not None:
        parts.append(
            "语速偏快" if chars_per_second >= 5.5 else "语速偏慢" if chars_per_second <= 3.2 else "语速适中"
        )
    if avg_sentence_length is not None:
        parts.append(
            "长句为主" if avg_sentence_length >= 20 else "短句为主" if avg_sentence_length <= 10 else "长短句交替"
        )
    if question_rate is not None:
        if question_rate >= 0.2:
            parts.append("习惯用设问句引导互动")
        elif question_rate == 0:
            parts.append("较少使用设问")
    if command_rate is not None and command_rate >= 0.15:
        parts.append("强带货指令型话术")
    if interjection_rate is not None and interjection_rate >= 0.05:
        parts.append("语气词较多、口语化明显")
    summary = "；".join(parts) or "风格特征不明显"
    return {
        "charsPerSecond": chars_per_second,
        "avgSentenceLength": avg_sentence_length,
        "segmentCount": segment_count,
        "charCount": char_count,
        "questionRate": question_rate,
        "commandRate": command_rate,
        "interjectionRate": interjection_rate,
        "summary": summary,
    }


def build_speaker_profiles(
    transcript: dict[str, Any],
) -> list[dict[str, Any]]:
    groups = _texts_by_speaker(transcript)
    profiles: list[dict[str, Any]] = []
    for speaker, texts in sorted(groups.items()):
        duration = 0.0
        for segment in transcript.get("segments") or []:
            if isinstance(segment, dict) and str(segment.get("speaker") or "_unassigned") == speaker:
                duration += max(
                    0.0,
                    float(segment.get("endSeconds") or 0) - float(segment.get("startSeconds") or 0),
                )
        profiles.append(
            {
                "speaker": speaker,
                "label": "未命名" if speaker == "_unassigned" else speaker,
                "durationSeconds": round(duration, 1),
                "topics": _frequent_ngrams(texts),
                "catchphrases": _catchphrases(texts),
                "style": _style_profile(texts, duration),
            }
        )
    return profiles


def attach_speaker_metrics(
    profiles: list[dict[str, Any]],
    phrases: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Attach spend/GMV/orders/ROI during each speaker's windows and rank them."""

    def number(value: Any) -> float:
        try:
            parsed = float(value)
            return parsed if parsed == parsed else 0.0
        except (TypeError, ValueError):
            return 0.0

    aggregate: dict[str, dict[str, float]] = {}
    for phrase in phrases:
        if not isinstance(phrase, dict):
            continue
        speaker = str(phrase.get("speaker") or "_unassigned")
        metrics = phrase.get("metrics") if isinstance(phrase.get("metrics"), dict) else {}
        bucket = aggregate.setdefault(speaker, {"spend": 0.0, "gmv": 0.0, "orders": 0.0})
        bucket["spend"] += number(metrics.get("spendDelta"))
        bucket["gmv"] += number(metrics.get("gmvDelta"))
        bucket["orders"] += number(metrics.get("ordersDelta"))

    for profile in profiles:
        bucket = aggregate.get(profile["speaker"], {"spend": 0.0, "gmv": 0.0, "orders": 0.0})
        spend = round(bucket["spend"], 2)
        gmv = round(bucket["gmv"], 2)
        orders = round(bucket["orders"], 4)
        roi = round(gmv / spend, 4) if spend > 0 else None
        duration_minutes = (float(profile.get("durationSeconds") or 0)) / 60.0
        orders_per_minute = (
            round(orders / duration_minutes, 2) if duration_minutes > 0 else None
        )
        profile["metrics"] = {
            "spend": spend,
            "gmv": gmv,
            "orders": orders,
            "roi": roi,
            "ordersPerMinute": orders_per_minute,
            "scope": "说话窗口关联值",
        }

    def rank_key(profile: dict[str, Any]) -> tuple[float, float]:
        metrics = profile.get("metrics") or {}
        roi = metrics.get("roi")
        opm = metrics.get("ordersPerMinute")
        return (
            roi if roi is not None else -1.0,
            opm if opm is not None else -1.0,
        )

    ranked = sorted(profiles, key=rank_key, reverse=True)
    for index, profile in enumerate(ranked):
        profile["rank"] = index + 1
        profile["best"] = index == 0 and len(ranked) > 1
    return ranked


def apply_speaker_map(
    profiles: list[dict[str, Any]],
    speaker_map: dict[str, Any],
) -> list[dict[str, Any]]:
    mapping = (
        speaker_map.get("speakers")
        if isinstance(speaker_map, dict)
        else {}
    )
    mapping = mapping if isinstance(mapping, dict) else {}
    for profile in profiles:
        reference = mapping.get(profile.get("speaker"))
        if isinstance(reference, dict) and str(reference.get("name") or "").strip():
            profile["name"] = str(reference.get("name")).strip()
            profile["face"] = str(reference.get("face") or "")
            profile["label"] = profile["name"]
        else:
            speaker = str(profile.get("speaker") or "")
            profile["name"] = (
                speaker
                if speaker
                and speaker not in {"_unassigned"}
                and not re.fullmatch(r"speaker_\d+", speaker)
                else ""
            )
            profile["face"] = ""
    return profiles
