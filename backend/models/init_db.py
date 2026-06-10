"""数据库初始化脚本"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .database import Base, Discussion, Participant, Message, Consensus
from .enums import DiscussionStatus, ParticipantRole, AgentPhase, ConsensusType, MessageType


def get_engine(db_url: str = "sqlite:///./ai_panel_studio.db", echo: bool = False):
    """获取数据库引擎"""
    return create_engine(db_url, echo=echo)


def init_database(engine):
    """初始化数据库表"""
    Base.metadata.create_all(engine)
    print("✅ 数据库表创建成功")


def _utc_now():
    """返回UTC时间"""
    return datetime.now(timezone.utc)


def _make_id():
    """生成UUID"""
    return str(uuid.uuid4())


def _create_discussion(topic: str, expert_count: int, max_rounds: int) -> Discussion:
    """创建讨论"""
    return Discussion(
        id=_make_id(),
        topic=topic,
        status=DiscussionStatus.PENDING,
        expert_count=expert_count,
        max_rounds=max_rounds,
        current_round=0,
        created_at=_utc_now(),
        updated_at=_utc_now(),
    )


def _create_participant(
    discussion_id: str,
    name: str,
    role: ParticipantRole,
    title: str,
    stance: str,
    color: str,
) -> Participant:
    """创建参与者"""
    return Participant(
        id=_make_id(),
        discussion_id=discussion_id,
        name=name,
        role=role,
        title=title,
        stance=stance,
        color=color,
        agent_phase=AgentPhase.IDLE,
    )


def seed_sample_data(session):
    """插入样例数据"""

    samples = [
        # 样例1: AI与未来教育
        {
            "discussion": {"topic": "AI与未来教育：人工智能将如何重塑教育体系？", "expert_count": 4, "max_rounds": 5},
            "participants": [
                {"name": "张明远", "role": ParticipantRole.MODERATOR, "title": "资深教育科技记者", "stance": "中立引导者，善于挖掘各方观点", "color": "#4A90D9"},
                {"name": "李教授", "role": ParticipantRole.EXPERT, "title": "北京师范大学教育技术学教授", "stance": "AI赋能教育的坚定支持者，主张个性化学习", "color": "#E74C3C"},
                {"name": "王校长", "role": ParticipantRole.EXPERT, "title": "知名中学校长", "stance": "务实派，关注AI落地的实际挑战", "color": "#2ECC71"},
                {"name": "陈博士", "role": ParticipantRole.EXPERT, "title": "儿童心理学专家", "stance": "关注AI对青少年心理发展的影响", "color": "#F39C12"},
                {"name": "赵工程师", "role": ParticipantRole.EXPERT, "title": "AI教育产品创始人", "stance": "技术乐观主义者，相信AI能解决教育公平问题", "color": "#9B59B6"},
            ],
        },
        # 样例2: 远程办公的未来
        {
            "discussion": {"topic": "远程办公的未来：混合办公是否会成为新常态？", "expert_count": 3, "max_rounds": 4},
            "participants": [
                {"name": "刘主编", "role": ParticipantRole.MODERATOR, "title": "商业周刊高级编辑", "stance": "理性观察者，关注趋势与数据", "color": "#3498DB"},
                {"name": "周HR", "role": ParticipantRole.EXPERT, "title": "跨国企业人力资源总监", "stance": "支持灵活办公，强调效率与员工满意度", "color": "#E67E22"},
                {"name": "吴经理", "role": ParticipantRole.EXPERT, "title": "传统制造业高管", "stance": "保守派，认为面对面协作不可替代", "color": "#1ABC9C"},
                {"name": "孙研究员", "role": ParticipantRole.EXPERT, "title": "组织行为学研究员", "stance": "关注远程办公对团队凝聚力的影响", "color": "#E74C3C"},
            ],
        },
        # 样例3: 数据隐私与AI
        {
            "discussion": {"topic": "数据隐私与AI发展：如何平衡创新与保护？", "expert_count": 4, "max_rounds": 5},
            "participants": [
                {"name": "马记者", "role": ParticipantRole.MODERATOR, "title": "科技深度报道记者", "stance": "追问者，致力于揭示技术背后的权力关系", "color": "#2C3E50"},
                {"name": "黄律师", "role": ParticipantRole.EXPERT, "title": "数据隐私法律专家", "stance": "严格保护个人隐私，支持强监管", "color": "#C0392B"},
                {"name": "林CTO", "role": ParticipantRole.EXPERT, "title": "互联网大厂技术副总裁", "stance": "主张技术自律，反对过度监管扼杀创新", "color": "#27AE60"},
                {"name": "何教授", "role": ParticipantRole.EXPERT, "title": "伦理学教授", "stance": "关注AI伦理，主张建立道德框架", "color": "#8E44AD"},
                {"name": "郑用户", "role": ParticipantRole.EXPERT, "title": "普通用户代表/数字权利倡导者", "stance": "为普通用户发声，关注知情权与选择权", "color": "#F1C40F"},
            ],
        },
        # 样例4: 气候变化与能源转型
        {
            "discussion": {"topic": "气候变化与能源转型：谁来承担转型成本？", "expert_count": 3, "max_rounds": 4},
            "participants": [
                {"name": "钱主播", "role": ParticipantRole.MODERATOR, "title": "环境议题知名主持人", "stance": "平衡各方，推动建设性对话", "color": "#16A085"},
                {"name": "高科学家", "role": ParticipantRole.EXPERT, "title": "气候科学家", "stance": "科学立场，强调紧迫性和行动必要性", "color": "#2980B9"},
                {"name": "郭企业家", "role": ParticipantRole.EXPERT, "title": "新能源企业CEO", "stance": "市场驱动转型，绿色经济是机遇", "color": "#27AE60"},
                {"name": "谢代表", "role": ParticipantRole.EXPERT, "title": "发展中国家能源政策顾问", "stance": "关注公平性，发达国家应承担更多责任", "color": "#D35400"},
            ],
        },
        # 样例5: 元宇宙与虚拟社交
        {
            "discussion": {"topic": "元宇宙与虚拟社交：人类的社交方式将被彻底改变吗？", "expert_count": 4, "max_rounds": 5},
            "participants": [
                {"name": "冯主持人", "role": ParticipantRole.MODERATOR, "title": "科技节目主持人", "stance": "好奇心驱动，善于引导深入讨论", "color": "#7F8C8D"},
                {"name": "韩工程师", "role": ParticipantRole.EXPERT, "title": "VR/AR技术专家", "stance": "技术信仰者，认为元宇宙是必然趋势", "color": "#3498DB"},
                {"name": "杨教授", "role": ParticipantRole.EXPERT, "title": "社会学教授", "stance": "审慎观察者，关注虚拟社交的异化风险", "color": "#E74C3C"},
                {"name": "秦设计师", "role": ParticipantRole.EXPERT, "title": "用户体验设计师", "stance": "以人为本，技术应服务于真实需求", "color": "#F39C12"},
                {"name": "许投资人", "role": ParticipantRole.EXPERT, "title": "科技领域风险投资人", "stance": "关注商业可行性与市场规模", "color": "#9B59B6"},
            ],
        },
    ]

    for sample in samples:
        d = _create_discussion(**sample["discussion"])
        session.add(d)
        for p in sample["participants"]:
            session.add(_create_participant(d.id, **p))

    session.commit()

    print("✅ 样例数据插入成功")
    for i, sample in enumerate(samples, 1):
        print(f"   - 讨论{i}: {sample['discussion']['topic']}")


def run_init():
    """运行初始化"""
    engine = get_engine()
    init_database(engine)

    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        existing = session.query(Discussion).count()
        if existing == 0:
            seed_sample_data(session)
        else:
            print(f"ℹ️  数据库已有 {existing} 条讨论记录，跳过初始化")
    except Exception as e:
        session.rollback()
        print(f"❌ 初始化失败: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    run_init()
