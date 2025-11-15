/**
 * Idea input component with dialogue mode and variation mode
 */

import { useState, useRef, useEffect } from 'react';
import { api } from '../lib/api';
import { getApiUrl } from '../lib/config';

interface Props {
  onSubmit: (text: string, skipFormatting?: boolean, formattedText?: string) => Promise<void>;
  sessionId?: string;
  enableDialogueMode?: boolean;
  enableVariationMode?: boolean;
}

type InputMode = 'direct' | 'dialogue' | 'variation';

export const IdeaInput = ({ onSubmit, sessionId, enableDialogueMode = true, enableVariationMode = true }: Props) => {
  const [text, setText] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [inputMode, setInputMode] = useState<InputMode>('direct');
  const [skipFormatting, setSkipFormatting] = useState(true);
  const [conversationHistory, setConversationHistory] = useState<Array<{ role: string; content: string }>>([]);
  const [aiResponse, setAiResponse] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [variations, setVariations] = useState<string[]>([]);
  const [selectedVariations, setSelectedVariations] = useState<Set<number>>(new Set());
  const [isGenerating, setIsGenerating] = useState(false);
  const [originalText, setOriginalText] = useState<string>(''); // Store user's original input
  const [isOriginalSelected, setIsOriginalSelected] = useState(false); // Track if original text is selected
  const [isFromExistingIdea, setIsFromExistingIdea] = useState(false); // Track if variations are from existing idea
  const [proposedIdea, setProposedIdea] = useState<string | null>(null); // Store proposed idea from LLM
  const [showProposalDialog, setShowProposalDialog] = useState(false); // Show confirmation dialog
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const chatHistoryRef = useRef<HTMLDivElement>(null); // Reference to chat history container

  // Auto-scroll chat history to bottom when new messages arrive
  useEffect(() => {
    if (chatHistoryRef.current) {
      chatHistoryRef.current.scrollTop = chatHistoryRef.current.scrollHeight;
    }
  }, [conversationHistory, aiResponse]);

  // Listen for external variation generation requests
  useEffect(() => {
    const handleGenerateVariations = async (event: Event) => {
      const customEvent = event as CustomEvent<{ text: string }>;
      const ideaText = customEvent.detail.text;

      // Switch to variation mode and set the text
      setInputMode('variation');
      setText(ideaText);
      setConversationHistory([]);
      setAiResponse('');

      // Automatically generate variations
      setIsGenerating(true);
      setError(null);
      setVariations([]);
      setSelectedVariations(new Set());
      setOriginalText(ideaText);
      setIsOriginalSelected(false);
      setIsFromExistingIdea(true); // Mark as from existing idea

      if (!sessionId) {
        setError('セッションIDが必要です');
        setIsGenerating(false);
        return;
      }

      try {
        const response = await api.dialogue.generateVariations({
          keyword: ideaText,
          session_id: sessionId,
          count: 10,
        });

        setVariations(response.variations);
      } catch (err) {
        console.error('Failed to generate variations:', err);
        setError('バリエーションの生成に失敗しました');
      } finally {
        setIsGenerating(false);
      }
    };

    window.addEventListener('generateVariationsFromIdea', handleGenerateVariations);
    return () => {
      window.removeEventListener('generateVariationsFromIdea', handleGenerateVariations);
    };
  }, [sessionId]);

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
      // Use new API with proposal system
      const result = await api.dialogue.deepenWithProposal({
        message: text.trim(),
        conversation_history: newHistory,
        session_id: sessionId!,
      });

      if (result.type === 'proposal') {
        // LLM is proposing to submit the idea
        setProposedIdea(result.verbalized_idea!);
        setAiResponse(result.content || `対話が深まりました。以下の内容で投稿してよろしいですか？\n\n「${result.verbalized_idea}」`);
        setShowProposalDialog(true);

        // Add AI response to history
        setConversationHistory([...newHistory, { role: 'assistant', content: result.content || '投稿を提案します' }]);
      } else {
        // LLM is continuing the conversation with a question
        setAiResponse(result.content);

        // Add AI response to history
        setConversationHistory([...newHistory, { role: 'assistant', content: result.content }]);
      }

      setText('');
    } catch (err) {
      console.error('Dialogue error:', err);
      setError('AIとの対話に失敗しました');
    } finally {
      setIsStreaming(false);
    }
  };

  const handleProposalAccept = async () => {
    if (!proposedIdea) return;

    setIsSubmitting(true);
    setError(null);
    setShowProposalDialog(false);

    try {
      // Submit the proposed idea (skip formatting since LLM already formatted it)
      await onSubmit(proposedIdea, true, proposedIdea);

      // Reset dialogue mode
      setInputMode('direct');
      setConversationHistory([]);
      setAiResponse('');
      setText('');
      setProposedIdea(null);
    } catch (err) {
      console.error('Failed to submit idea:', err);
      setError('アイディアの投稿に失敗しました');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleProposalReject = () => {
    setShowProposalDialog(false);
    setProposedIdea(null);
    // User can continue the conversation
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
      const response = await fetch(`${getApiUrl()}/api/dialogue/finalize`, {
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
      setInputMode('direct');
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

  const handleGenerateVariations = async () => {
    if (!text.trim()) {
      setError('キーワードを入力してください');
      return;
    }

    if (!sessionId) {
      setError('セッションIDが必要です');
      return;
    }

    setIsGenerating(true);
    setError(null);
    setVariations([]);
    setSelectedVariations(new Set());
    setOriginalText(text.trim()); // Save the original user input
    setIsOriginalSelected(false); // Reset original selection
    setIsFromExistingIdea(false); // Not from existing idea

    try {
      const response = await api.dialogue.generateVariations({
        keyword: text.trim(),
        session_id: sessionId,
        count: 10,
      });

      setVariations(response.variations);
    } catch (err) {
      console.error('Failed to generate variations:', err);
      setError('バリエーションの生成に失敗しました');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleToggleVariation = (index: number) => {
    const newSelected = new Set(selectedVariations);
    if (newSelected.has(index)) {
      newSelected.delete(index);
    } else {
      newSelected.add(index);
    }
    setSelectedVariations(newSelected);
  };

  const handleSubmitVariations = async () => {
    if (selectedVariations.size === 0 && !isOriginalSelected) {
      setError('少なくとも1つのアイディアを選択してください');
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      const submitPromises = [];

      // Submit original text if selected
      if (isOriginalSelected && originalText) {
        submitPromises.push(onSubmit(originalText, true)); // skip_formatting = true
      }

      // Submit all selected variations in parallel
      // raw_text = originalText (拡張前の原文)
      // formatted_text = variation (拡張後のテキスト)
      submitPromises.push(
        ...Array.from(selectedVariations).map(index =>
          onSubmit(originalText, false, variations[index]) // raw_text=originalText, formatted_text=variation
        )
      );

      await Promise.all(submitPromises);

      // Reset variation data but stay in variation mode
      setText('');
      setVariations([]);
      setSelectedVariations(new Set());
      setOriginalText(''); // Clear original text
      setIsOriginalSelected(false); // Clear original selection
      setIsFromExistingIdea(false); // Clear existing idea flag
      // Keep inputMode as 'variation'
    } catch (err) {
      console.error('Failed to submit variations:', err);
      setError('アイディアの投稿に失敗しました');
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

    if (inputMode === 'dialogue') {
      // In dialogue mode, continue conversation
      await handleDialogueContinue();
    } else if (inputMode === 'variation') {
      // In variation mode, generate variations
      await handleGenerateVariations();
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
      {/* Mode toggle - only show if at least one AI mode is enabled */}
      {(enableDialogueMode || enableVariationMode) && (
      <div style={{ marginBottom: '0.75rem', display: 'flex', gap: '0.5rem' }}>
        <button
          type="button"
          onClick={() => {
            setInputMode('direct');
            setConversationHistory([]);
            setAiResponse('');
            setVariations([]);
            setSelectedVariations(new Set());
            setOriginalText('');
            setIsOriginalSelected(false);
            setIsFromExistingIdea(false);
          }}
          style={{
            flex: 1,
            padding: '0.5rem',
            background: inputMode === 'direct' ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : '#f0f0f0',
            color: inputMode === 'direct' ? 'white' : '#666',
            border: 'none',
            borderRadius: '0.5rem',
            fontSize: '0.875rem',
            fontWeight: '600',
            cursor: 'pointer',
          }}
        >
          直接投稿
        </button>
        {enableDialogueMode && (
          <button
            type="button"
            onClick={() => {
              setInputMode('dialogue');
              setVariations([]);
              setSelectedVariations(new Set());
              setOriginalText('');
              setIsOriginalSelected(false);
              setIsFromExistingIdea(false);
            }}
            style={{
              flex: 1,
              padding: '0.5rem',
              background: inputMode === 'dialogue' ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : '#f0f0f0',
              color: inputMode === 'dialogue' ? 'white' : '#666',
              border: 'none',
              borderRadius: '0.5rem',
              fontSize: '0.875rem',
              fontWeight: '600',
              cursor: 'pointer',
            }}
          >
            💬 AI対話
          </button>
        )}
        {enableVariationMode && (
          <button
            type="button"
            onClick={() => {
              setInputMode('variation');
              setConversationHistory([]);
              setAiResponse('');
            }}
            style={{
              flex: 1,
              padding: '0.5rem',
              background: inputMode === 'variation' ? 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)' : '#f0f0f0',
              color: inputMode === 'variation' ? 'white' : '#666',
              border: 'none',
              borderRadius: '0.5rem',
              fontSize: '0.875rem',
              fontWeight: '600',
              cursor: 'pointer',
            }}
          >
            ✨ AIバリエーション
          </button>
        )}
      </div>
      )}

      {/* Variations display */}
      {inputMode === 'variation' && variations.length > 0 && (
        <div style={{
          marginBottom: '0.75rem',
          border: '1px solid #e0e0e0',
          borderRadius: '0.5rem',
          padding: '0.75rem',
          background: '#fafafa',
        }}>
          <div style={{ fontWeight: '600', marginBottom: '0.5rem', fontSize: '0.95rem' }}>
            生成されたアイディア（選択して投稿）:
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            {/* Display original text first with checkbox */}
            {originalText && (
              <label
                style={{
                  display: 'flex',
                  alignItems: 'start',
                  gap: '0.5rem',
                  padding: '0.5rem',
                  background: isFromExistingIdea ? '#f5f5f5' : (isOriginalSelected ? '#fff3cd' : '#fff9e6'),
                  border: `2px solid ${isFromExistingIdea ? '#ccc' : (isOriginalSelected ? '#ffc107' : '#ffd700')}`,
                  borderRadius: '0.5rem',
                  cursor: isFromExistingIdea ? 'not-allowed' : 'pointer',
                  transition: 'all 0.2s',
                  opacity: isFromExistingIdea ? 0.6 : 1,
                }}
                onMouseEnter={(e) => {
                  if (!isOriginalSelected && !isFromExistingIdea) {
                    e.currentTarget.style.borderColor = '#ffb300';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!isOriginalSelected && !isFromExistingIdea) {
                    e.currentTarget.style.borderColor = '#ffd700';
                  }
                }}
              >
                <input
                  type="checkbox"
                  checked={isOriginalSelected}
                  onChange={() => !isFromExistingIdea && setIsOriginalSelected(!isOriginalSelected)}
                  disabled={isFromExistingIdea}
                  style={{
                    width: '18px',
                    height: '18px',
                    marginTop: '2px',
                    cursor: isFromExistingIdea ? 'not-allowed' : 'pointer',
                    flexShrink: 0,
                  }}
                />
                <div style={{ fontSize: '0.875rem', lineHeight: '1.4' }}>
                  <div style={{ fontWeight: '600', marginBottom: '0.25rem', color: isFromExistingIdea ? '#999' : '#856404' }}>
                    📝 原文: {isFromExistingIdea && <span style={{ fontSize: '0.75rem', fontWeight: 'normal' }}>(既に投稿済み)</span>}
                  </div>
                  <div style={{ color: isFromExistingIdea ? '#999' : 'inherit' }}>{originalText}</div>
                </div>
              </label>
            )}
            {variations.map((variation, index) => (
              <label
                key={index}
                style={{
                  display: 'flex',
                  alignItems: 'start',
                  gap: '0.5rem',
                  padding: '0.5rem',
                  background: selectedVariations.has(index) ? '#e3f2fd' : 'white',
                  border: `2px solid ${selectedVariations.has(index) ? '#667eea' : '#e0e0e0'}`,
                  borderRadius: '0.5rem',
                  cursor: 'pointer',
                  transition: 'all 0.2s',
                }}
                onMouseEnter={(e) => {
                  if (!selectedVariations.has(index)) {
                    e.currentTarget.style.borderColor = '#bbb';
                  }
                }}
                onMouseLeave={(e) => {
                  if (!selectedVariations.has(index)) {
                    e.currentTarget.style.borderColor = '#e0e0e0';
                  }
                }}
              >
                <input
                  type="checkbox"
                  checked={selectedVariations.has(index)}
                  onChange={() => handleToggleVariation(index)}
                  style={{
                    width: '18px',
                    height: '18px',
                    marginTop: '2px',
                    cursor: 'pointer',
                    flexShrink: 0,
                  }}
                />
                <span style={{ fontSize: '0.875rem', lineHeight: '1.4' }}>
                  {variation}
                </span>
              </label>
            ))}
          </div>
          <div style={{ marginTop: '0.5rem', fontSize: '0.875rem', color: '#666' }}>
            {selectedVariations.size + (isOriginalSelected ? 1 : 0)}個のアイディアを選択中
          </div>
        </div>
      )}

      {/* Conversation history */}
      {inputMode === 'dialogue' && conversationHistory.length > 0 && (
        <div
          ref={chatHistoryRef}
          style={{
            marginBottom: '0.75rem',
            maxHeight: '300px',
            overflowY: 'auto',
            border: '1px solid #e0e0e0',
            borderRadius: '0.5rem',
            padding: '0.75rem',
            background: '#fafafa',
          }}
        >
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

      {/* Proposal Dialog */}
      {showProposalDialog && proposedIdea && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'rgba(0, 0, 0, 0.5)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
        }}>
          <div style={{
            background: 'white',
            borderRadius: '1rem',
            padding: '2rem',
            maxWidth: '500px',
            width: '90%',
            boxShadow: '0 4px 20px rgba(0, 0, 0, 0.15)',
          }}>
            <h3 style={{ marginTop: 0, marginBottom: '1rem', fontSize: '1.25rem' }}>
              アイディアの投稿確認
            </h3>
            <p style={{ color: '#666', marginBottom: '1rem' }}>
              対話が深まりました。以下の内容で投稿してよろしいですか？
            </p>
            <div style={{
              background: '#f5f5f5',
              borderRadius: '0.5rem',
              padding: '1rem',
              marginBottom: '1.5rem',
              border: '2px solid #667eea',
            }}>
              <p style={{ margin: 0, fontSize: '1rem', lineHeight: '1.5' }}>
                「{proposedIdea}」
              </p>
            </div>
            <div style={{ display: 'flex', gap: '1rem' }}>
              <button
                onClick={handleProposalReject}
                disabled={isSubmitting}
                style={{
                  flex: 1,
                  padding: '0.75rem',
                  background: '#f0f0f0',
                  color: '#666',
                  border: 'none',
                  borderRadius: '0.5rem',
                  fontSize: '1rem',
                  fontWeight: '600',
                  cursor: isSubmitting ? 'not-allowed' : 'pointer',
                  opacity: isSubmitting ? 0.5 : 1,
                }}
              >
                いいえ、続ける
              </button>
              <button
                onClick={handleProposalAccept}
                disabled={isSubmitting}
                style={{
                  flex: 1,
                  padding: '0.75rem',
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  color: 'white',
                  border: 'none',
                  borderRadius: '0.5rem',
                  fontSize: '1rem',
                  fontWeight: '600',
                  cursor: isSubmitting ? 'not-allowed' : 'pointer',
                  opacity: isSubmitting ? 0.5 : 1,
                }}
              >
                {isSubmitting ? '投稿中...' : 'はい、投稿する'}
              </button>
            </div>
          </div>
        </div>
      )}

      <div style={{ marginBottom: '0.75rem' }}>
        <label style={{
          display: 'block',
          marginBottom: '0.5rem',
          fontWeight: '600',
          fontSize: '0.95rem',
        }}>
          💡 {
            inputMode === 'dialogue'
              ? 'AIと対話しながらアイディアを深める'
              : inputMode === 'variation'
                ? 'キーワードから複数のアイディアを生成'
                : '新しいアイディアを投稿'
          }
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
          placeholder={
            inputMode === 'variation'
              ? 'キーワードを入力してください（例: 環境問題、リモートワーク）'
              : 'あなたのアイディアを入力してください...'
          }
          rows={inputMode === 'variation' ? 2 : 3}
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
            {inputMode === 'dialogue'
              ? 'AIと対話しながらアイディアを磨きます'
              : inputMode === 'variation'
                ? 'AIが10種類のバリエーションを生成します'
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
      {inputMode === 'direct' && (
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

      {/* Submit buttons based on mode */}
      {inputMode === 'dialogue' ? (
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
      ) : inputMode === 'variation' ? (
        <div style={{ display: 'flex', gap: '0.5rem' }}>
          <button
            type="submit"
            disabled={isGenerating || !text.trim() || variations.length > 0}
            style={{
              flex: 1,
              padding: '0.75rem',
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: 'white',
              border: 'none',
              borderRadius: '0.5rem',
              fontSize: '1rem',
              fontWeight: '600',
              cursor: isGenerating || !text.trim() || variations.length > 0 ? 'not-allowed' : 'pointer',
              opacity: isGenerating || !text.trim() || variations.length > 0 ? 0.6 : 1,
              transition: 'opacity 0.2s',
            }}
          >
            {isGenerating ? '生成中...' : '✨ バリエーション生成'}
          </button>
          {variations.length > 0 && (
            <button
              type="button"
              onClick={handleSubmitVariations}
              disabled={isSubmitting || selectedVariations.size === 0}
              style={{
                flex: 1,
                padding: '0.75rem',
                background: 'linear-gradient(135deg, #f093fb 0%, #f5576c 100%)',
                color: 'white',
                border: 'none',
                borderRadius: '0.5rem',
                fontSize: '1rem',
                fontWeight: '600',
                cursor: isSubmitting || selectedVariations.size === 0 ? 'not-allowed' : 'pointer',
                opacity: isSubmitting || selectedVariations.size === 0 ? 0.6 : 1,
                transition: 'opacity 0.2s',
              }}
            >
              {isSubmitting ? '投稿中...' : `✓ ${selectedVariations.size}個を投稿`}
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
