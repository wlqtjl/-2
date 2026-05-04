#!/usr/bin/env python3
"""场景包种子脚本 — 把 SmartX HCI Deploy + IOPS 场景写入数据库。

用法：
    cd backend
    ./venv/bin/python seed_scenarios.py
    # 或者直接在 backend 目录运行：python seed_scenarios.py
"""
import sys, os

# 确保 backend 目录在 Python 路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from apps.core.database import SessionLocal, engine
from apps.core.models import Base, Scenario, ScenarioStatus

# 建表（幂等，只创建不存在的表）
Base.metadata.create_all(bind=engine)

SMARTX_HCI_SCENARIO = {
    "meta": {
        "id": "smartx-hci-deploy-iops-v1",
        "name": "SmartX 超融合部署 + IOPS 性能验证",
        "version": "1.0.0",
        "domain": "storage",
        "difficulty": "intermediate",
        "locale": "zh-CN",
        "timeLimit": 1800
    },
    # 不设 intro_video → 自动展示主题正确的文字简报卡片（不会泄露 V2V intro）
    "intro_video": None,
    "narrative": {
        "briefing": "侦察报告显示生产集群已满载。你的任务：在 30 分钟内完成三节点 SmartX 超融合部署，并通过 fio 压测验证 IOPS 达标。任何配置失误都会让存储网络崩溃——务必精准。",
        "success": "所有节点上线，IOPS 达标，学习报告已生成。任务完成。",
        "failure": "集群初始化失败或 IOPS 未达标。系统已回滚，请查看复盘报告。",
        "npcName": "技术主管陈博士"
    },
    "stages": [
        {
            "id": "s1_briefing",
            "title": "任务简报",
            "type": "briefing",
            "description": "陈博士介绍背景，展示目标拓扑图",
            "weight": 0,
            "onPass": "s2_network_plan"
        },
        {
            "id": "s2_network_plan",
            "title": "网络规划",
            "type": "question",
            "description": "规划存储网络与管理网络分离方案",
            "weight": 20,
            "questions": [
                {
                    "id": "q1",
                    "type": "single",
                    "stem": "SmartX 超融合中，存储网络（vMotion/数据复制）推荐使用哪种网络隔离方式？",
                    "options": [
                        {"key": "A", "label": "与管理网络共用同一 VLAN，方便统一管控"},
                        {"key": "B", "label": "独立 VLAN + 万兆专用交换机，确保低延迟"},
                        {"key": "C", "label": "使用 WiFi 降低布线成本"},
                        {"key": "D", "label": "所有流量走公网，云化部署"}
                    ],
                    "correctAnswer": "B",
                    "explanation": "存储网络对延迟和带宽敏感，必须与管理网络物理或逻辑隔离，独立万兆链路是最佳实践。",
                    "points": 10,
                    "hint": "考虑 IO 路径上的延迟抖动"
                },
                {
                    "id": "q2",
                    "type": "multi",
                    "stem": "三节点超融合集群的最低网络要求包括哪些？（多选）",
                    "options": [
                        {"key": "A", "label": "每节点至少 2 × 10GbE 存储口"},
                        {"key": "B", "label": "管理网络 1GbE 即可"},
                        {"key": "C", "label": "节点间 RTT ≤ 1ms"},
                        {"key": "D", "label": "需要专属 40GbE 链路才能运行"}
                    ],
                    "correctAnswer": ["A", "B", "C"],
                    "explanation": "10GbE 存储口和低延迟是强制要求；管理网络 1GbE 可接受；40GbE 是可选优化，不是最低要求。",
                    "points": 10
                }
            ],
            "onPass": "s3_deploy_steps",
            "onFail": "s3_deploy_steps"
        },
        {
            "id": "s3_deploy_steps",
            "title": "部署步骤",
            "type": "question",
            "description": "按正确顺序完成集群初始化操作",
            "weight": 30,
            "questions": [
                {
                    "id": "q3",
                    "type": "steps",
                    "stem": "请将以下步骤拖拽排列为正确的 SmartX 集群初始化顺序：",
                    "options": [
                        {"key": "1", "label": "配置 BMC / IPMI 管理地址"},
                        {"key": "2", "label": "安装 ELF 操作系统"},
                        {"key": "3", "label": "配置存储网络 IP"},
                        {"key": "4", "label": "创建集群并加入节点"},
                        {"key": "5", "label": "配置 vStore 存储池"},
                        {"key": "6", "label": "创建虚拟机网络"}
                    ],
                    "correctAnswer": ["1", "2", "3", "4", "5", "6"],
                    "explanation": "先底层硬件管理，再 OS，再网络，再集群，再存储，最后上层网络资源。",
                    "points": 20
                },
                {
                    "id": "q4",
                    "type": "config",
                    "stem": "创建三副本存储池时，容错因子（FTT）应设置为多少？",
                    "correctAnswer": "1",
                    "explanation": "FTT=1 即数据保存 2 份，三节点集群可容忍 1 节点故障，这是最小可用生产配置。",
                    "points": 10
                }
            ],
            "onPass": "s4_iops_test",
            "onFail": "s4_iops_test"
        },
        {
            "id": "s4_iops_test",
            "title": "IOPS 性能测试",
            "type": "question",
            "description": "设计 fio 测试方案并解读结果",
            "weight": 30,
            "questions": [
                {
                    "id": "q5",
                    "type": "single",
                    "stem": "使用 fio 测试随机 4K 读 IOPS 时，以下哪个参数组合最合理？",
                    "options": [
                        {"key": "A", "label": "--bs=4k --rw=randread --iodepth=1 --numjobs=1"},
                        {"key": "B", "label": "--bs=4k --rw=randread --iodepth=128 --numjobs=4"},
                        {"key": "C", "label": "--bs=1m --rw=read --iodepth=1 --numjobs=1"},
                        {"key": "D", "label": "--bs=512k --rw=randwrite --iodepth=8"}
                    ],
                    "correctAnswer": "B",
                    "explanation": "4K 随机读需要高队列深度和多 job 并发才能充分压测存储层，iodepth=128 + numjobs=4 是通用基准。",
                    "points": 15
                },
                {
                    "id": "q6",
                    "type": "config",
                    "stem": "三节点 SmartX 全闪集群，三副本，客户要求随机 4K 读 IOPS ≥ 200,000。你的测试结果为 215,000 IOPS。是否达标？填写 yes 或 no。",
                    "correctAnswer": "yes",
                    "explanation": "215,000 > 200,000，超过目标阈值，达标。",
                    "points": 15
                }
            ],
            "onPass": "s5_validate",
            "onFail": "s5_validate"
        },
        {
            "id": "s5_validate",
            "title": "机器校验",
            "type": "validate",
            "description": "系统自动验证集群健康状态和 IOPS 指标",
            "weight": 10,
            "validator": {
                "type": "threshold",
                "metric": "iops_4k_randread",
                "operator": "gte",
                "target": 200000
            },
            "completionCondition": "集群三节点均在线 + 4K 随机读 IOPS ≥ 200,000",
            "onPass": "s6_summary",
            "onFail": "s6_summary"
        },
        {
            "id": "s6_summary",
            "title": "任务总结",
            "type": "summary",
            "description": "展示得分、各维度评分和个性化学习建议",
            "weight": 10,
            "onPass": "__end__"
        }
    ],
    "scoring": {
        "passingScore": 70,
        "maxScore": 100,
        "dimensions": [
            {"name": "部署规范", "weight": 0.5},
            {"name": "性能达标", "weight": 0.5}
        ],
        "penaltyRules": [
            {"trigger": "wrong_answer",  "deductPct": 5},
            {"trigger": "hint_used",     "deductPct": 3},
            {"trigger": "timeout",       "deductPct": 10}
        ]
    }
}

# ---------------------------------------------------------------------------
# V2V 迁移场景（原有 FPS 游戏内容的 DSL 化版本，方便日后替换硬编码数据）
# ---------------------------------------------------------------------------
V2V_MIGRATION_SCENARIO = {
    "meta": {
        "id": "v2v-migration-v1",
        "name": "SmartX V2V 数据迁移战役",
        "version": "1.0.0",
        "domain": "storage",
        "difficulty": "intermediate",
        "locale": "zh-CN",
        "timeLimit": 0
    },
    # V2V 主题与 bundle 自带 intro 一致，沿用原始开场视频
    "intro_video": "/game/intro.mp4",
    "narrative": {
        "briefing": "生产虚拟机需要从旧存储平台迁移到 SmartX 超融合平台。你将完成扫描、兼容性检查、网络/存储映射、数据同步、驱动注入、切换和验证全流程。",
        "success": "V2V 迁移完成！业务零中断，数据完整性 100%。",
        "failure": "迁移失败，请检查错误日志并重试。",
        "npcName": "运维指挥官"
    },
    "stages": [
        {
            "id": "s1_scan",
            "title": "虚拟机扫描",
            "type": "action",
            "description": "扫描源端 VM 配置、磁盘、网络适配器",
            "weight": 15,
            "onPass": "s2_compat"
        },
        {
            "id": "s2_compat",
            "title": "兼容性检查",
            "type": "action",
            "description": "验证 CPU 指令集、驱动版本、磁盘格式兼容性",
            "weight": 15,
            "onPass": "s3_map"
        },
        {
            "id": "s3_map",
            "title": "网络/存储映射",
            "type": "action",
            "description": "配置源-目标网络映射和存储池映射",
            "weight": 20,
            "onPass": "s4_sync"
        },
        {
            "id": "s4_sync",
            "title": "数据同步",
            "type": "action",
            "description": "增量同步 VM 磁盘数据，监控同步进度",
            "weight": 25,
            "onPass": "s5_cutover"
        },
        {
            "id": "s5_cutover",
            "title": "驱动注入 & 切换",
            "type": "action",
            "description": "注入 virtio 驱动，执行切换窗口",
            "weight": 15,
            "onPass": "s6_verify"
        },
        {
            "id": "s6_verify",
            "title": "迁移验证",
            "type": "validate",
            "description": "验证业务连通性和数据完整性",
            "weight": 10,
            "validator": {
                "type": "comparison",
                "metric": "data_integrity_pct",
                "operator": "gte",
                "target": 100
            },
            "completionCondition": "所有 VM 在目标平台正常运行，数据完整性 100%",
            "onPass": "__end__",
            "onFail": "__end__"
        }
    ],
    "scoring": {
        "passingScore": 60,
        "maxScore": 100,
        "penaltyRules": [
            {"trigger": "wrong_answer", "deductPct": 5},
            {"trigger": "timeout",      "deductPct": 10}
        ]
    }
}

SEEDS = [
    ("smartx-hci-deploy-iops-v1", SMARTX_HCI_SCENARIO),
    ("v2v-migration-v1",          V2V_MIGRATION_SCENARIO),
]


def run():
    db = SessionLocal()
    try:
        created = updated = skipped = 0
        for slug, payload in SEEDS:
            existing = db.query(Scenario).filter(Scenario.scenario_id == slug).first()
            if existing:
                # 只更新 payload 和名称，保留用户手动修改的 status
                existing.payload = payload
                existing.name = payload["meta"]["name"]
                existing.domain = payload["meta"].get("domain")
                existing.difficulty = payload["meta"].get("difficulty")
                existing.version = payload["meta"].get("version", "1.0.0")
                db.commit()
                print(f"[UPDATED]  {slug}")
                updated += 1
            else:
                obj = Scenario(
                    scenario_id=slug,
                    name=payload["meta"]["name"],
                    domain=payload["meta"].get("domain"),
                    difficulty=payload["meta"].get("difficulty"),
                    version=payload["meta"].get("version", "1.0.0"),
                    status=ScenarioStatus.PUBLISHED,
                    payload=payload,
                )
                db.add(obj)
                db.commit()
                print(f"[CREATED]  {slug}")
                created += 1

        print(f"\n完成：新建 {created}，更新 {updated}，跳过 {skipped}")
    except Exception as exc:
        db.rollback()
        print(f"[ERROR] {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    run()
