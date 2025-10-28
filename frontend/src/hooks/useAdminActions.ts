/**
 * Custom hook for admin actions (cluster recalculation, etc.)
 */

import { useState } from 'react';
import { api } from '../lib/api';

interface UseAdminActionsOptions {
  sessionId: string;
  onSuccess?: () => void;
  onError?: (error: string) => void;
}

interface UseAdminActionsReturn {
  showAdminDialog: boolean;
  adminPassword: string;
  clusteringInProgress: boolean;
  clusterMode: 'auto' | 'fixed';
  fixedClusterCount: string;
  setShowAdminDialog: (show: boolean) => void;
  setAdminPassword: (password: string) => void;
  setClusterMode: (mode: 'auto' | 'fixed') => void;
  setFixedClusterCount: (count: string) => void;
  handleRecalculateClick: (ideaCount: number) => void;
  handleAdminSubmit: (e: React.FormEvent) => Promise<void>;
}

export const useAdminActions = ({
  sessionId,
  onSuccess,
  onError,
}: UseAdminActionsOptions): UseAdminActionsReturn => {
  const [showAdminDialog, setShowAdminDialog] = useState(false);
  const [adminPassword, setAdminPassword] = useState('');
  const [clusteringInProgress, setClusteringInProgress] = useState(false);
  const [clusterMode, setClusterMode] = useState<'auto' | 'fixed'>('auto');
  const [fixedClusterCount, setFixedClusterCount] = useState('');

  const handleRecalculateClick = (ideaCount: number) => {
    if (ideaCount < 10) {
      alert('クラスタ再計算にはアイディアが10件以上必要です');
      return;
    }
    setShowAdminDialog(true);
  };

  const handleAdminSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    try {
      const result = await api.auth.verifyAdmin(adminPassword);
      if (!result.success) {
        onError?.('管理者認証に失敗しました');
        return;
      }

      setClusteringInProgress(true);
      setShowAdminDialog(false);
      setAdminPassword('');

      // Prepare fixed_cluster_count parameter
      const fixedCount =
        clusterMode === 'fixed' && fixedClusterCount
          ? parseInt(fixedClusterCount, 10)
          : null;

      await api.debug.forceCluster(sessionId, true, fixedCount);

      alert('クラスタリングが完了しました');
      onSuccess?.();
    } catch (err) {
      console.error('Failed to recalculate clustering:', err);
      onError?.('クラスタリングの再計算に失敗しました');
    } finally {
      setClusteringInProgress(false);
    }
  };

  return {
    showAdminDialog,
    adminPassword,
    clusteringInProgress,
    clusterMode,
    fixedClusterCount,
    setShowAdminDialog,
    setAdminPassword,
    setClusterMode,
    setFixedClusterCount,
    handleRecalculateClick,
    handleAdminSubmit,
  };
};
