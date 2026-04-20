from __future__ import annotations


class KnowledgeClassifier:
    DOMAIN_RULES: dict[str, list[str]] = {
        "ai": ["模型", "embedding", "prompt", "rag", "attention", "transformer"],
        "engineering": ["接口", "api", "部署", "性能", "日志", "测试"],
        "product": ["需求", "用户", "体验", "流程", "设计"],
    }

    def classify(self, text: str) -> tuple[str, list[str]]:
        lowered = text.lower()
        hits: list[tuple[str, int]] = []
        tags: list[str] = []
        for domain, keywords in self.DOMAIN_RULES.items():
            score = 0
            for kw in keywords:
                if kw.lower() in lowered:
                    score += 1
                    tags.append(kw.lower())
            hits.append((domain, score))
        hits.sort(key=lambda x: x[1], reverse=True)
        top_domain = hits[0][0] if hits and hits[0][1] > 0 else "general"
        unique_tags = sorted(set(tags))
        return top_domain, unique_tags
