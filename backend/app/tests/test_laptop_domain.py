from app.agents.mvp_agents import build_profile, extract_companies


def test_explicit_laptop_competitors_keep_product_lines() -> None:
    query = "分析任务：请分析笔记本电脑品类的竞品，包括 MacBook Air、华硕、联想小新、惠普。其他说明：价格限定在6000元档。"

    assert extract_companies(query) == ["MacBook Air", "华硕", "联想小新", "惠普"]


def test_auto_discovery_instruction_is_not_a_competitor() -> None:
    query = "任务模式：AI发现竞品。品类：4000元价格档手机。竞品数量：5。其他说明：关注性能、屏幕、续航。"

    assert extract_companies(query) == []


def test_laptop_profile_uses_hardware_schema() -> None:
    profile = build_profile(
        "proj_test",
        "MacBook Air",
        [
            {
                "url": "https://www.apple.com.cn/macbook-air/",
                "source_type": "official",
                "content": (
                    "MacBook Air 13 英寸，M3 processor，Liquid Retina display，轻薄设计，"
                    "最高 18 小时续航，支持 Thunderbolt 接口。价格 RMB 7999 起。"
                ),
            }
        ],
        "laptop computer / consumer electronics",
    )

    feature_names = {feature["name"] for feature in profile["features"]}
    assert profile["product_category"] == "laptop computer / consumer electronics"
    assert "性能与芯片" in feature_names
    assert "屏幕显示" in feature_names
    assert "续航与充电" in feature_names
    assert "AI writing" not in feature_names
    assert profile["pricing"][0]["price"] == "observed price signals: ¥7999"
    assert profile["business_model"] == ["hardware retail"]
