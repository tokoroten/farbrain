/**
 * Idea input component with dialogue mode
 */

import { useState, useRef } from 'react';

interface Props {
  onSubmit: (text: string, skipFormatting?: boolean) => Promise<void>;
  sessionId?: string;
}

export const IdeaInput = ({ onSubmit, sessionId }: Props) => {
  const [text, setText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [dialogueMode, setDialogueMode] = useState(false);
  const [skipFormatting, setSkipFormatting] = useState(true);
  const [conversationHistory, setConversationHistory] = useState<Array<{ role: string; content: string }>>([]);
  const [aiResponse, setAiResponse] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleDialogueContinue = async () => {
    if (!text.trim()) {
      setError('メッセージを入力してください');
      return;
    }

    setError(null);
    setIsStreaming(true);
    setAiResponse('');

    // Add user message to history
    const newHistory = [...conversationHistory, { role: 'user', content: text.trim() }];
    setConversationHistory(newHistory);

    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/dialogue/deepen`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text.trim(),
          conversation_history: newHistory,
          session_id: sessionId,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to get AI response');
      }

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No response stream');

      const decoder = new TextDecoder();
      let fullResponse = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value);
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const data = line.slice(6);
            if (data === '[DONE]') {
              break;
            } else if (data.startsWith('[ERROR]')) {
              throw new Error(data.slice(8));
            } else {
              fullResponse += data;
              setAiResponse(fullResponse);
            }
          }
        }
      }

      // Add AI response to history
      setConversationHistory([...newHistory, { role: 'assistant', content: fullResponse }]);
      setText('');
    } catch (err) {
      console.error('Dialogue error:', err);
      setError('AIとの対話に失敗しました');
    } finally {
      setIsStreaming(false);
    }
  };

  const handleDialogueFinalize = async () => {
    setIsSubmitting(true);
    setError(null);

    // Check if we have either text or conversation history
    if (!text.trim() && conversationHistory.length === 0) {
      setError('メッセージを入力するか、AIと対話してください');
      setIsSubmitting(false);
      return;
    }

    try {
      const response = await fetch(`${import.meta.env.VITE_API_URL}/api/dialogue/finalize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text.trim(),
          conversation_history: conversationHistory,
          session_id: sessionId,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to finalize idea');
      }

      const data = await response.json();

      // Show message if idea was generated from conversation
      if (data.from_conversation) {
        console.log('Idea synthesized from conversation history');
      }

      await onSubmit(data.formatted_idea);

      // Reset dialogue mode
      setDialogueMode(false);
      setConversationHistory([]);
      setAiResponse('');
      setText('');
    } catch (err) {
      console.error('Failed to finalize idea:', err);
      setError('アイディアの確定に失敗しました');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (!text.trim()) {
      setError('アイディアを入力してください');
      return;
    }

    if (text.length > 2000) {
      setError('アイディアは2000文字以内で入力してください');
      return;
    }

    if (dialogueMode) {
      // In dialogue mode, continue conversation
      await handleDialogueContinue();
    } else {
      // Direct submission - optimistic UI
      const ideaText = text.trim();
      const currentSkipFormatting = skipFormatting;

      // Clear input immediately and return focus
      setText('');
      setTimeout(() => {
        textareaRef.current?.focus();
      }, 0);

      // Submit in background (fire-and-forget with error handling)
      onSubmit(ideaText, currentSkipFormatting).catch((err) => {
        console.error('Failed to submit idea:', err);
        setError('アイディアの送信に失敗しました。もう一度お試しください。');
        // Restore text on error
        setText(ideaText);
      });
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      {/* Mode toggle */}
      <div style={{ marginBottom: '0.75rem', display: 'flex', gap: '0.5rem' }}>
        <button
          type="button"
          onClick={() => {
            setDialogueMode(false);
            setConversationHistory([]);
            setAiResponse('');
          }}
          style={{
            flex: 1,
            padding: '0.5rem',
            background: !dialogueMode ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : '#f0f0f0',
            color: !dialogueMode ? 'white' : '#666',
            border: 'none',
            borderRadius: '0.5rem',
            fontSize: '0.875rem',
            fontWeight: '600',
            cursor: 'pointer',
          }}
        >
          直接投稿
        </button>
        <button
          type="button"
          onClick={() => setDialogueMode(true)}
          style={{
            flex: 1,
            padding: '0.5rem',
            background: dialogueMode ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : '#f0f0f0',
            color: dialogueMode ? 'white' : '#666',
            border: 'none',
            borderRadius: '0.5rem',
            fontSize: '0.875rem',
            fontWeight: '600',
            cursor: 'pointer',
          }}
        >
          💬 AI対話モード
        </button>
      </div>

      {/* Conversation history */}
      {dialogueMode && conversationHistory.length > 0 && (
        <div style={{
          marginBottom: '0.75rem',
          maxHeight: '300px',
          overflowY: 'auto',
          border: '1px solid #e0e0e0',
          borderRadius: '0.5rem',
          padding: '0.75rem',
          background: '#fafafa',
        }}>
          {conversationHistory.map((msg, idx) => (
            <div
              key={idx}
              style={{
                marginBottom: '0.5rem',
                padding: '0.5rem',
                background: msg.role === 'user' ? '#e3f2fd' : '#f3e5f5',
                borderRadius: '0.5rem',
                fontSize: '0.875rem',
              }}
            >
              <div style={{ fontWeight: '600', marginBottom: '0.25rem' }}>
                {msg.role === 'user' ? 'あなた' : 'AI'}:
              </div>
              <div>{msg.content}</div>
            </div>
          ))}
          {isStreaming && (
            <div style={{
              padding: '0.5rem',
              background: '#f3e5f5',
              borderRadius: '0.5rem',
              fontSize: '0.875rem',
            }}>
              <div style={{ fontWeight: '600', marginBottom: '0.25rem' }}>AI:</div>
              <div>{aiResponse}</div>
            </div>
          )}
        </div>
      )}

      <div style={{ marginBottom: '0.75rem' }}>
        <label style={{
          display: 'block',
          marginBottom: '0.5rem',
          fontWeight: '600',
          fontSize: '0.95rem',
        }}>
          💡 {dialogueMode ? 'AIと対話しながらアイディアを深める' : '新しいアイディアを投稿'}
        </label>
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            // Ctrl+Enter to submit
            if (e.ctrlKey && e.key === 'Enter') {
              e.preventDefault();
              handleSubmit(e as any);
            }
          }}
          placeholder="あなたのアイディアを入力してください..."
          rows={3}
          maxLength={2000}
          style={{
            width: '100%',
            padding: '0.75rem',
            border: '2px solid #e0e0e0',
            borderRadius: '0.5rem',
            fontSize: '1rem',
            boxSizing: 'border-box',
            resize: 'vertical',
            fontFamily: 'inherit',
          }}
          onFocus={(e) => e.target.style.borderColor = '#667eea'}
          onBlur={(e) => e.target.style.borderColor = '#e0e0e0'}
        />
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginTop: '0.25rem',
          fontSize: '0.875rem',
          color: '#666',
        }}>
          <span>
            {dialogueMode
              ? 'AIと対話しながらアイディアを磨きます'
              : skipFormatting
                ? '入力したアイディアをそのまま可視化します'
                : 'AIがアイディアをブラッシュアップして可視化します'
            }
          </span>
          <span>
            {text.length} / 2000
          </span>
        </div>
      </div>

      {/* LLM Formatting checkbox (only in direct mode) */}
      {!dialogueMode && (
        <div style={{ marginBottom: '0.75rem' }}>
          <label style={{
            display: 'flex',
            alignItems: 'center',
            gap: '0.5rem',
            fontSize: '0.875rem',
            cursor: 'pointer',
            userSelect: 'none',
          }}>
            <input
              type="checkbox"
              checked={!skipFormatting}
              onChange={(e) => setSkipFormatting(!e.target.checked)}
              style={{
                width: '18px',
                height: '18px',
                cursor: 'pointer',
              }}
            />
            <span>AIでアイディアをブラッシュアップする</span>
            <span style={{ color: '#999', fontSize: '0.8rem' }}>
              （オフの場合、入力したテキストがそのまま投稿されます）
            </span>
          </label>
        </div>
      )}

      {error && (
        <div style={{
          padding: '0.5rem',
          marginBottom: '0.75rem',
          background: '#fee',
          border: '1px solid #fcc',
          borderRadius: '0.5rem',
          color: '#c33',
          fontSize: '0.875rem',
        }}>
          {error}
        </div>
      )}

      {dialogueMode ? (
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            type="submit"
            disabled={isStreaming || !text.trim()}
            style={{
              flex: 1,
              padding: '0.75rem',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: 'white',
              border: 'none',
              borderRadius: '0.5rem',
              fontSize: '1rem',
              fontWeight: '600',
              cursor: isStreaming || !text.trim() ? 'not-allowed' : 'pointer',
              opacity: isStreaming || !text.trim() ? 0.6 : 1,
              transition: 'opacity 0.2s',
            }}
          >
            {isStreaming ? '対話中...' : 'AIと対話'}
          </button>
          {conversationHistory.length > 0 && (
            <button
              type="button"
              onClick={handleDialogueFinalize}
              disabled={isSubmitting}
              style={{
                flex: 1,
                padding: '0.75rem',
                background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                color: 'white',
                border: 'none',
                borderRadius: '0.5rem',
                fontSize: '1rem',
                fontWeight: '600',
                cursor: isSubmitting ? 'not-allowed' : 'pointer',
                opacity: isSubmitting ? 0.6 : 1,
                transition: 'opacity 0.2s',
              }}
            >
              {isSubmitting ? '投稿中...' : '✓ 投稿する'}
            </button>
          )}
        </div>
      ) : (
        <button
          type="submit"
          disabled={!text.trim()}
          style={{
            width: '100%',
            padding: '0.75rem',
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: 'white',
            border: 'none',
            borderRadius: '0.5rem',
            fontSize: '1rem',
            fontWeight: '600',
            cursor: !text.trim() ? 'not-allowed' : 'pointer',
            opacity: !text.trim() ? 0.6 : 1,
            transition: 'opacity 0.2s',
          }}
        >
          投稿する
        </button>
      )}
    </form>
  );
};
