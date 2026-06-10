'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { listDiscussions } from '@/lib/api';
import { Discussion } from '@/lib/types';

const QUICK_TOPICS = [
  'AI 会取代程序员吗？',
  '远程办公 vs 现场办公',
  '新能源汽车的未来',
  '教育改革方向',
  '数字货币的前景',
];

export default function HomePage() {
  const [discussions, setDiscussions] = useState<Discussion[]>([]);
  const [loading, setLoading] = useState(true);
  const [topic, setTopic] = useState('');
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');
  const router = useRouter();

  useEffect(() => {
    loadDiscussions();
  }, []);

  const loadDiscussions = async () => {
    try {
      const result = await listDiscussions();
      if (result.ok) setDiscussions(result.discussions);
    } catch (err) {
      console.error('Failed to load discussions:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    if (!topic.trim()) { setError('请输入讨论话题'); return; }
    setGenerating(true);
    setError('');
    try {
      const { generateGuests, createDiscussion, confirmDiscussion } = await import('@/lib/api');
      const guests = await generateGuests(topic, 3);
      if (!guests.ok) { setError('嘉宾生成失败'); setGenerating(false); return; }

      const disc = await createDiscussion(topic, guests.host, guests.experts, 2);
      if (disc.ok) {
        await confirmDiscussion(disc.discussion_id);
        router.push(`/studio/${disc.discussion_id}`);
      } else {
        setError('创建讨论失败');
      }
    } catch {
      setError('网络错误，请重试');
    } finally {
      setGenerating(false);
    }
  };

  const getStatusBadge = (status: string) => {
    const map: Record<string, { cls: string; label: string }> = {
      assembling: { cls: 'badge-assembling', label: '筹备中' },
      active: { cls: 'badge-active', label: '进行中' },
      concluded: { cls: 'badge-concluded', label: '已结束' },
    };
    return map[status] || { cls: '', label: status };
  };

  return (
    <div className="page-enter">
      {/* Quick Create */}
      <div className="create-form" style={{ marginBottom: '2rem' }}>
        <div className="form-group" style={{ marginBottom: '0.75rem' }}>
          <label>快速发起讨论</label>
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            <input
              type="text"
              value={topic}
              onChange={(e) => { setTopic(e.target.value); setError(''); }}
              placeholder="输入任何你想探讨的话题..."
              className="input"
              onKeyDown={(e) => e.key === 'Enter' && !generating && handleCreate()}
              style={{ flex: 1 }}
            />
            <button onClick={handleCreate} disabled={generating || !topic.trim()} className="btn btn-primary">
              {generating ? '生成中...' : '开始讨论'}
            </button>
          </div>
          <div className="quick-topics">
            {QUICK_TOPICS.map((t) => (
              <button key={t} className="quick-topic" onClick={() => setTopic(t)}>{t}</button>
            ))}
          </div>
        </div>
        {error && <div className="error-msg">{error}</div>}
      </div>

      {/* Discussion List */}
      <div className="home-header">
        <h2>讨论列表</h2>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '3rem 0', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '0.8rem' }}>
          <div className="spinner"></div>
          <p>正在加载...</p>
        </div>
      ) : discussions.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '3rem 0', color: 'var(--text-muted)' }}>
          <p>暂无讨论 — 在上方输入话题开始</p>
        </div>
      ) : (
        <div className="discussion-list">
          {discussions.map((disc, index) => {
            const badge = getStatusBadge(disc.status);
            return (
              <div key={disc.id} className="discussion-card" onClick={() => router.push(`/studio/${disc.id}`)}>
                <div className="card-index">{String(index + 1).padStart(2, '0')}</div>
                <div className="card-body">
                  <div className="card-header-row">
                    <h3>{disc.topic}</h3>
                    <span className={`badge ${badge.cls}`}>{badge.label}</span>
                  </div>
                  <div className="card-meta">
                    <span>{disc.participant_count || 0} 位嘉宾</span>
                    <span>R{disc.current_round}/{disc.max_rounds}</span>
                    {disc.convergence_score !== null && (
                      <span>共识 {Math.round(disc.convergence_score * 100)}%</span>
                    )}
                  </div>
                  {disc.status === 'concluded' && disc.conclusion && (
                    <div className="card-conclusion">{disc.conclusion}</div>
                  )}
                </div>
                {disc.status === 'active' && (
                  <div className="card-action"><span className="btn btn-sm">进入 →</span></div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
