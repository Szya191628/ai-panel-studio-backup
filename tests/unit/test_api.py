"""API路由单元测试"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import sys
sys.path.insert(0, "D:/ai-panel-studio")

from backend.main import app
from backend.core.database import get_db
from backend.models.database import Base
from backend.models import DiscussionStatus, ParticipantRole


# 使用文件数据库进行测试
TEST_DATABASE_URL = "sqlite:///./test_api.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """覆盖数据库依赖"""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database():
    """每个测试前重建数据库"""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


# ==================== 健康检查测试 ====================

class TestHealth:
    """健康检查接口测试"""

    def test_health_check(self):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "app" in data
        assert "version" in data


# ==================== 讨论管理测试 ====================

class TestDiscussions:
    """讨论管理接口测试"""

    def test_create_discussion(self):
        """测试创建讨论"""
        response = client.post("/api/discussions", json={
            "topic": "AI与未来教育",
            "expert_count": 4,
            "max_rounds": 5,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["topic"] == "AI与未来教育"
        assert data["status"] == "pending"
        assert data["expert_count"] == 4
        assert data["max_rounds"] == 5

    def test_create_discussion_defaults(self):
        """测试创建讨论使用默认值"""
        response = client.post("/api/discussions", json={
            "topic": "测试话题",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["expert_count"] == 4
        assert data["max_rounds"] == 5

    def test_create_discussion_invalid_topic(self):
        """测试创建讨论 - 无效话题"""
        response = client.post("/api/discussions", json={
            "topic": "A",  # 太短
        })
        assert response.status_code == 422

    def test_create_discussion_invalid_expert_count(self):
        """测试创建讨论 - 无效专家人数"""
        response = client.post("/api/discussions", json={
            "topic": "测试话题",
            "expert_count": 1,  # 小于最小值
        })
        assert response.status_code == 422

    def test_list_discussions(self):
        """测试获取讨论列表"""
        # 先创建一个讨论
        client.post("/api/discussions", json={"topic": "测试话题1"})
        client.post("/api/discussions", json={"topic": "测试话题2"})

        response = client.get("/api/discussions")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_list_discussions_with_status_filter(self):
        """测试按状态筛选讨论"""
        client.post("/api/discussions", json={"topic": "测试话题1"})
        client.post("/api/discussions", json={"topic": "测试话题2"})

        response = client.get("/api/discussions?status=pending")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_get_discussion(self):
        """测试获取讨论详情"""
        create_response = client.post("/api/discussions", json={"topic": "测试话题"})
        discussion_id = create_response.json()["id"]

        response = client.get(f"/api/discussions/{discussion_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == discussion_id
        assert data["topic"] == "测试话题"

    def test_get_discussion_not_found(self):
        """测试获取不存在的讨论"""
        response = client.get("/api/discussions/nonexistent")
        assert response.status_code == 404

    def test_delete_discussion(self):
        """测试删除讨论"""
        create_response = client.post("/api/discussions", json={"topic": "测试话题"})
        discussion_id = create_response.json()["id"]

        response = client.delete(f"/api/discussions/{discussion_id}")
        assert response.status_code == 200
        assert response.json()["message"] == "讨论已删除"

        # 验证已删除
        response = client.get(f"/api/discussions/{discussion_id}")
        assert response.status_code == 404

    def test_delete_discussion_not_found(self):
        """测试删除不存在的讨论"""
        response = client.delete("/api/discussions/nonexistent")
        assert response.status_code == 404


# ==================== 参与者管理测试 ====================

class TestParticipants:
    """参与者管理接口测试"""

    def _create_discussion_with_participants(self):
        """辅助方法：创建讨论并添加参与者"""
        # 创建讨论
        disc_response = client.post("/api/discussions", json={
            "topic": "测试话题",
            "expert_count": 3,
        })
        discussion_id = disc_response.json()["id"]

        # 添加主持人
        mod_response = client.post(f"/api/participants/{discussion_id}", json={
            "name": "主持人",
            "role": "moderator",
            "title": "资深主持人",
            "stance": "中立",
            "color": "#4A90D9",
        })

        # 添加专家
        expert1_response = client.post(f"/api/participants/{discussion_id}", json={
            "name": "专家1",
            "role": "expert",
            "title": "领域专家1",
            "stance": "支持",
            "color": "#E74C3C",
        })
        expert2_response = client.post(f"/api/participants/{discussion_id}", json={
            "name": "专家2",
            "role": "expert",
            "title": "领域专家2",
            "stance": "反对",
            "color": "#2ECC71",
        })

        return discussion_id, mod_response, expert1_response, expert2_response

    def test_create_participant(self):
        """测试创建参与者"""
        disc_response = client.post("/api/discussions", json={"topic": "测试话题"})
        discussion_id = disc_response.json()["id"]

        response = client.post(f"/api/participants/{discussion_id}", json={
            "name": "张教授",
            "role": "expert",
            "title": "AI研究员",
            "stance": "支持AI发展",
            "color": "#FF0000",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "张教授"
        assert data["role"] == "expert"

    def test_create_moderator(self):
        """测试创建主持人"""
        disc_response = client.post("/api/discussions", json={"topic": "测试话题"})
        discussion_id = disc_response.json()["id"]

        response = client.post(f"/api/participants/{discussion_id}", json={
            "name": "主持人",
            "role": "moderator",
            "title": "资深主持人",
            "stance": "中立",
            "color": "#4A90D9",
        })
        assert response.status_code == 200
        data = response.json()
        assert data["role"] == "moderator"

    def test_create_duplicate_moderator(self):
        """测试创建重复主持人"""
        disc_response = client.post("/api/discussions", json={"topic": "测试话题"})
        discussion_id = disc_response.json()["id"]

        # 创建第一个主持人
        client.post(f"/api/participants/{discussion_id}", json={
            "name": "主持人1",
            "role": "moderator",
            "title": "资深主持人",
            "stance": "中立",
            "color": "#4A90D9",
        })

        # 尝试创建第二个主持人
        response = client.post(f"/api/participants/{discussion_id}", json={
            "name": "主持人2",
            "role": "moderator",
            "title": "资深主持人",
            "stance": "中立",
            "color": "#3498DB",
        })
        assert response.status_code == 400
        assert "主持人已存在" in response.json()["detail"]

    def test_create_expert_beyond_limit(self):
        """测试创建专家超出限制"""
        disc_response = client.post("/api/discussions", json={
            "topic": "测试话题",
            "expert_count": 2,
        })
        discussion_id = disc_response.json()["id"]

        # 创建2个专家
        client.post(f"/api/participants/{discussion_id}", json={
            "name": "专家1", "role": "expert", "title": "专家", "stance": "支持", "color": "#FF0000",
        })
        client.post(f"/api/participants/{discussion_id}", json={
            "name": "专家2", "role": "expert", "title": "专家", "stance": "反对", "color": "#00FF00",
        })

        # 尝试创建第3个专家
        response = client.post(f"/api/participants/{discussion_id}", json={
            "name": "专家3", "role": "expert", "title": "专家", "stance": "中立", "color": "#0000FF",
        })
        assert response.status_code == 400
        assert "专家人数已达到上限" in response.json()["detail"]

    def test_list_participants(self):
        """测试获取参与者列表"""
        discussion_id, _, _, _ = self._create_discussion_with_participants()

        response = client.get(f"/api/participants/{discussion_id}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3  # 1主持人 + 2专家

    def test_delete_participant(self):
        """测试删除参与者"""
        disc_response = client.post("/api/discussions", json={"topic": "测试话题"})
        discussion_id = disc_response.json()["id"]

        # 创建参与者
        create_response = client.post(f"/api/participants/{discussion_id}", json={
            "name": "专家",
            "role": "expert",
            "title": "专家",
            "stance": "支持",
            "color": "#FF0000",
        })
        participant_id = create_response.json()["id"]

        # 删除参与者
        response = client.delete(f"/api/participants/{discussion_id}/{participant_id}")
        assert response.status_code == 200
        assert response.json()["message"] == "参与者已删除"

    def test_delete_participant_not_found(self):
        """测试删除不存在的参与者"""
        disc_response = client.post("/api/discussions", json={"topic": "测试话题"})
        discussion_id = disc_response.json()["id"]

        response = client.delete(f"/api/participants/{discussion_id}/nonexistent")
        assert response.status_code == 404


# ==================== 讨论启动测试 ====================

class TestDiscussionStart:
    """讨论启动接口测试"""

    def test_start_discussion(self):
        """测试启动讨论"""
        # 创建讨论
        disc_response = client.post("/api/discussions", json={
            "topic": "测试话题",
            "expert_count": 2,
        })
        discussion_id = disc_response.json()["id"]

        # 添加主持人
        client.post(f"/api/participants/{discussion_id}", json={
            "name": "主持人", "role": "moderator", "title": "主持人", "stance": "中立", "color": "#4A90D9",
        })

        # 添加专家
        client.post(f"/api/participants/{discussion_id}", json={
            "name": "专家1", "role": "expert", "title": "专家", "stance": "支持", "color": "#E74C3C",
        })
        client.post(f"/api/participants/{discussion_id}", json={
            "name": "专家2", "role": "expert", "title": "专家", "stance": "反对", "color": "#2ECC71",
        })

        # 启动讨论
        response = client.post(f"/api/discussions/{discussion_id}/start")
        assert response.status_code == 200
        assert response.json()["status"] == "debating"

    def test_start_discussion_without_moderator(self):
        """测试没有主持人时启动讨论"""
        disc_response = client.post("/api/discussions", json={
            "topic": "测试话题",
            "expert_count": 2,
        })
        discussion_id = disc_response.json()["id"]

        # 只添加专家，不添加主持人
        client.post(f"/api/participants/{discussion_id}", json={
            "name": "专家1", "role": "expert", "title": "专家", "stance": "支持", "color": "#E74C3C",
        })
        client.post(f"/api/participants/{discussion_id}", json={
            "name": "专家2", "role": "expert", "title": "专家", "stance": "反对", "color": "#2ECC71",
        })

        response = client.post(f"/api/discussions/{discussion_id}/start")
        assert response.status_code == 400
        assert "缺少主持人" in response.json()["detail"]

    def test_start_discussion_without_experts(self):
        """测试没有专家时启动讨论"""
        disc_response = client.post("/api/discussions", json={
            "topic": "测试话题",
            "expert_count": 2,
        })
        discussion_id = disc_response.json()["id"]

        # 只添加主持人
        client.post(f"/api/participants/{discussion_id}", json={
            "name": "主持人", "role": "moderator", "title": "主持人", "stance": "中立", "color": "#4A90D9",
        })

        response = client.post(f"/api/discussions/{discussion_id}/start")
        assert response.status_code == 400
        assert "专家人数不足" in response.json()["detail"]

    def test_start_discussion_already_started(self):
        """测试重复启动讨论"""
        disc_response = client.post("/api/discussions", json={
            "topic": "测试话题",
            "expert_count": 2,
        })
        discussion_id = disc_response.json()["id"]

        # 添加参与者
        client.post(f"/api/participants/{discussion_id}", json={
            "name": "主持人", "role": "moderator", "title": "主持人", "stance": "中立", "color": "#4A90D9",
        })
        client.post(f"/api/participants/{discussion_id}", json={
            "name": "专家1", "role": "expert", "title": "专家", "stance": "支持", "color": "#E74C3C",
        })
        client.post(f"/api/participants/{discussion_id}", json={
            "name": "专家2", "role": "expert", "title": "专家", "stance": "反对", "color": "#2ECC71",
        })

        # 第一次启动
        client.post(f"/api/discussions/{discussion_id}/start")

        # 尝试再次启动
        response = client.post(f"/api/discussions/{discussion_id}/start")
        assert response.status_code == 400
        assert "无法启动" in response.json()["detail"]


# ==================== 讨论停止测试 ====================

class TestDiscussionStop:
    """讨论停止接口测试"""

    def test_stop_discussion(self):
        """测试停止讨论"""
        # 创建并启动讨论
        disc_response = client.post("/api/discussions", json={
            "topic": "测试话题",
            "expert_count": 2,
        })
        discussion_id = disc_response.json()["id"]

        client.post(f"/api/participants/{discussion_id}", json={
            "name": "主持人", "role": "moderator", "title": "主持人", "stance": "中立", "color": "#4A90D9",
        })
        client.post(f"/api/participants/{discussion_id}", json={
            "name": "专家1", "role": "expert", "title": "专家", "stance": "支持", "color": "#E74C3C",
        })
        client.post(f"/api/participants/{discussion_id}", json={
            "name": "专家2", "role": "expert", "title": "专家", "stance": "反对", "color": "#2ECC71",
        })
        client.post(f"/api/discussions/{discussion_id}/start")

        # 停止讨论
        response = client.post(f"/api/discussions/{discussion_id}/stop")
        assert response.status_code == 200
        assert response.json()["status"] == "finished"

    def test_stop_discussion_not_started(self):
        """测试停止未开始的讨论"""
        disc_response = client.post("/api/discussions", json={"topic": "测试话题"})
        discussion_id = disc_response.json()["id"]

        response = client.post(f"/api/discussions/{discussion_id}/stop")
        assert response.status_code == 400
        assert "无法停止" in response.json()["detail"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
