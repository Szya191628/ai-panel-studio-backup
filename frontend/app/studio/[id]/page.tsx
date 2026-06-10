'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  getDiscussion,
  runDiscussion,
  endDiscussion,
  createSSEConnection,
} from '@/lib/api';
import { Participant, Speech, Findings } from '@/lib/types';

function getAvatar(seed: string, isHost = false) {
  const bg = isHost ? 'ffdfbf' : 'b6e3f4';
  return `https://api.dicebear.com/7.x/personas/svg?seed=${seed}&backgroundColor=${bg}`;
}

interface SpeechEx extends Speech {
  name?: string;
  job_title?: string;
}

export default function StudioPage() {
  const params = useParams();
  const router = useRouter();
  const discussionId = params?.id as string;

  const [topic, setTopic] = useState('');
  const [status, setStatus] = useState('');
  const [currentRound, setCurrentRound] = useState(0);
  const [maxRounds, setMaxRounds] = useState(5);
  const [participants, setParticipants] = useState<Participant[]>([]);
  const [speeches, setSpeeches] = useState<SpeechEx[]>([]);
  const [findings, setFindings] = useState<Findings>({ consensus: [], disagreements: [] });
  const [conclusion, setConclusion] = useState<string | null>(null);
  const [convergence, setConvergence] = useState<number | null>(null);
  const [streamContent, setStreamContent] = useState('');
  const [streamSpeaker, setStreamSpeaker] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [thinking, setThinking] = useState<{
    pid: string; stage: 'thinking' | 'draft' | 'final'; content: string;
  } | null>(null);

  const transcriptRef = useRef<HTMLDivElement>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (discussionId) { load(); setupSSE(); }
    return () => { esRef.current?.close(); };
  }, [discussionId]);

  useEffect(() => {
    transcriptRef.current?.scrollTo({ top: transcriptRef.current.scrollHeight, behavior: 'smooth' });
  }, [speeches, streamContent, thinking]);

  const load = async () => {
    try {
      const r = await getDiscussion(discussionId);
      if (r.ok) {
        setTopic(r.discussion.topic);
        setStatus(r.discussion.status);
        setCurrentRound(r.discussion.current_round);
        setMaxRounds(r.discussion.max_rounds);
        setParticipants(r.participants);
        setSpeeches(r.speeches);
        setFindings(r.findings);
        setConclusion(r.discussion.conclusion);
        setConvergence(r.discussion.convergence_score);
      }
    } catch (e) { console.error(e); }
  };

  const setupSSE = () => {
    const es = createSSEConnection(discussionId, (ev, d) => {
      switch (ev) {
        case 'speech_start':
          setStreamSpeaker(d.name); setStreamContent(''); setThinking(null);
          setParticipants(p => p.map(x => x.id === d.participant_id ? { ...x, status: 'speaking' } : x));
          break;
        case 'speech_token': setStreamContent(c => c + d.content); break;
        case 'speech_end': setStreamSpeaker(null); setStreamContent(''); setThinking(null); break;
        case 'speech':
          setSpeeches(s => [...s, d]);
          setParticipants(p => p.map(x => x.id === d.participant_id ? { ...x, status: 'standby' } : x));
          break;
        case 'finding_update':
          setFindings(f => d.type === 'consensus'
            ? { ...f, consensus: [...f.consensus, d.content] }
            : { ...f, disagreements: [...f.disagreements, d.content] });
          break;
        case 'round_summary': setCurrentRound(d.round); setConvergence(d.convergence); break;
        case 'status_change': setStatus(d.status); if (d.conclusion) setConclusion(d.conclusion); break;
        case 'participant_status':
          setParticipants(p => p.map(x => x.id === d.participant_id
            ? { ...x, status: d.status, thinking_summary: d.thinking_summary } : x));
          break;
        case 'thinking': setThinking({ pid: d.participant_id, stage: 'thinking', content: d.content }); break;
        case 'draft': setThinking({ pid: d.participant_id, stage: 'draft', content: d.content }); break;
        case 'speech_evolution': if (d.stage === 'final') setThinking(null); break;
      }
    });
    esRef.current = es;
  };

  const getParticipant = (id: string) => participants.find(p => p.id === id);
  const host = participants.find(p => p.is_host);
  const experts = participants.filter(p => !p.is_host);

  return (
    <div className="studio-page page-enter">
      {/* Control Bar */}
      <div className="studio-header">
        <div className="header-left">
          {status === 'active' && <span className="on-air">ON AIR</span>}
          <h2>{topic}</h2>
          <span className="round-info">R{currentRound}/{maxRounds}</span>
          {convergence !== null && <span className="convergence">共识 {Math.round(convergence * 100)}%</span>}
        </div>
        <div className="header-right">
          {status === 'active' && (
            <>
              <button onClick={async () => { setIsRunning(true); try { await runDiscussion(discussionId); } catch {} finally { setIsRunning(false); } }}
                disabled={isRunning} className="btn btn-primary">
                {isRunning ? '运行中...' : '自动运行'}
              </button>
              <button onClick={() => endDiscussion(discussionId)} className="btn btn-danger">结束</button>
            </>
          )}
          <button onClick={() => router.push('/')} className="btn">返回</button>
        </div>
      </div>

      {/* Participants */}
      <div className="participant-panels">
        {host && (
          <div className={`participant-panel ${host.status}`}>
            <div className="panel-avatar"><img src={getAvatar(host.avatar_seed, true)} alt="" /></div>
            <div className="panel-info">
              <h4>{host.name}</h4>
              <p>{host.job_title}</p>
              <span className={`status-badge status-${host.status}`}>
                {host.status === 'standby' ? '待机' : host.status === 'preparing' ? '准备' : '发言'}
              </span>
              {host.thinking_summary && <p className="thinking-text">{host.thinking_summary}</p>}
            </div>
          </div>
        )}
        {experts.map(e => (
          <div key={e.id} className={`participant-panel ${e.status}`}>
            <div className="panel-avatar"><img src={getAvatar(e.avatar_seed)} alt="" /></div>
            <div className="panel-info">
              <h4>{e.name}</h4>
              <p>{e.job_title}</p>
              <span className={`status-badge status-${e.status}`}>
                {e.status === 'standby' ? '待机' : e.status === 'preparing' ? '准备' : '发言'}
              </span>
              {e.thinking_summary && <p className="thinking-text">{e.thinking_summary}</p>}
            </div>
          </div>
        ))}
      </div>

      {/* Thinking Process */}
      {thinking && thinking.stage !== 'final' && (
        <div className="thinking-process">
          <div className="thinking-head">
            <span className="thinking-icon">🧠</span>
            <span className="thinking-label">{getParticipant(thinking.pid)?.name} 正在思考</span>
          </div>
          <div>
            <span className={`stage-badge ${thinking.stage}`}>
              {thinking.stage === 'thinking' ? '分析' : '草稿'}
            </span>
            <span className="stage-text">{thinking.content}</span>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="studio-content">
        <div className="transcript-panel">
          <div className="panel-title">讨论记录</div>
          <div className="transcript-body" ref={transcriptRef}>
            {speeches.map((s, i) => {
              const p = getParticipant(s.participant_id);
              return (
                <div key={i} className="speech-item">
                  <div className="speech-avatar"><img src={getAvatar(p?.avatar_seed || '', p?.is_host)} alt="" /></div>
                  <div className="speech-body">
                    <div className="speech-head">
                      <span className="speech-name">{p?.name || '未知'}</span>
                      <span className="speech-role">{p?.job_title}</span>
                      <span className="speech-round">R{s.round}</span>
                    </div>
                    <div className="speech-text">{s.content}</div>
                  </div>
                </div>
              );
            })}

            {streamSpeaker && (
              <div className="speech-item streaming">
                <div className="speech-avatar"><img src={getAvatar('stream')} alt="" /></div>
                <div className="speech-body">
                  <div className="speech-head">
                    <span className="speech-name">{streamSpeaker}</span>
                    <span className="live-tag">● LIVE</span>
                  </div>
                  <div className="speech-text">{streamContent}<span className="cursor-blink">|</span></div>
                </div>
              </div>
            )}

            {speeches.length === 0 && !streamSpeaker && (
              <div className="empty-state-box">
                {status === 'assembling' ? '等待开始讨论...' : '暂无发言记录'}
              </div>
            )}
          </div>
        </div>

        <div className="findings-panel">
          <div className="panel-title">共识与分歧</div>

          <div className="findings-section">
            <h4>共识点</h4>
            {findings.consensus.length > 0 ? (
              <ul>{findings.consensus.map((c, i) => <li key={i} className="consensus-item">{c}</li>)}</ul>
            ) : <p className="empty-hint">暂无共识</p>}
          </div>

          <div className="findings-section">
            <h4>分歧点</h4>
            {findings.disagreements.length > 0 ? (
              <ul>{findings.disagreements.map((d, i) => <li key={i} className="disagreement-item">{d}</li>)}</ul>
            ) : <p className="empty-hint">暂无分歧</p>}
          </div>

          {conclusion && (
            <div className="conclusion-block">
              <h4>讨论总结</h4>
              <div className="conclusion-text">{conclusion}</div>
            </div>
          )}
        </div>
      </div>

      {/* Concluded Overlay */}
      {status === 'concluded' && (
        <div className="status-overlay">
          <div className="overlay-box">
            <h2>讨论已结束</h2>
            {conclusion && <p>{conclusion}</p>}
            <button onClick={() => router.push('/')} className="btn btn-primary btn-lg">返回首页</button>
          </div>
        </div>
      )}
    </div>
  );
}
