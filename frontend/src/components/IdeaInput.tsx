/**
 * Idea input component
 */

import { useState } from 'react';

interface Props {
  onSubmit: (text: string) => Promise<void>;
}

export const IdeaInput = ({ onSubmit }: Props) => {
  const [text, setText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

    setIsSubmitting(true);

    try {
      await onSubmit(text.trim());
      setText('');
    } catch (err) {
      console.error('Failed to submit idea:', err);
      setError('アイディアの送信に失敗しました');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit}>
      <div style={{ marginBottom: '0.75rem' }}>
        <label style={{
          display: 'block',
          marginBottom: '0.5rem',
          fontWeight: '600',
          fontSize: '0.95rem',
        }}>
          💡 新しいアイディアを投稿
        </label>
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          placeholder="あなたのアイディアを入力してください..."
          rows={3}
          maxLength={2000}
          disabled={isSubmitting}
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
          marginTop: '0.25rem',
          fontSize: '0.875rem',
          color: '#666',
        }}>
          <span>
            LLMが自動で整形して可視化します
          </span>
          <span>
            {text.length} / 2000
          </span>
        </div>
      </div>

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

      <button
        type="submit"
        disabled={isSubmitting || !text.trim()}
        style={{
          width: '100%',
          padding: '0.75rem',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          color: 'white',
          border: 'none',
          borderRadius: '0.5rem',
          fontSize: '1rem',
          fontWeight: '600',
          cursor: isSubmitting || !text.trim() ? 'not-allowed' : 'pointer',
          opacity: isSubmitting || !text.trim() ? 0.6 : 1,
          transition: 'opacity 0.2s',
        }}
      >
        {isSubmitting ? '送信中...' : '投稿する'}
      </button>
    </form>
  );
};
