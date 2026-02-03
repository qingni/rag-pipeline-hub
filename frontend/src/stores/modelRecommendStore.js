/**
 * Model recommendation state management.
 * 
 * Manages:
 * - Recommendation results
 * - Document analysis cache
 * - Model capability data
 */
import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import modelRecommendService from '../services/modelRecommendService';

export const useModelRecommendStore = defineStore('modelRecommend', () => {
  // State
  const recommendations = ref([]);
  const documentAnalysis = ref(null);
  const topRecommendation = ref(null);
  const batchResult = ref(null);
  const availableModels = ref([]);
  const recommendationWeights = ref(null);
  
  // Loading states
  const isLoading = ref(false);
  const isAnalyzing = ref(false);
  const isLoadingModels = ref(false);
  
  // Error state
  const error = ref(null);
  
  // Selected model (for use with embedding)
  const selectedModel = ref('');
  
  // Computed
  const hasRecommendations = computed(() => recommendations.value.length > 0);
  
  const hasOutliers = computed(() => {
    return batchResult.value?.has_outliers || false;
  });
  
  const outlierDocuments = computed(() => {
    return batchResult.value?.outlier_documents || [];
  });
  
  const textModels = computed(() => {
    return availableModels.value.filter(m => m.model_type === 'text');
  });
  
  const multimodalModels = computed(() => {
    return availableModels.value.filter(m => m.model_type === 'multimodal');
  });
  
  // Actions
  
  /**
   * Get recommendation for a single document.
   */
  const recommendForDocument = async (documentId, documentName, chunks, topN = 3) => {
    isLoading.value = true;
    error.value = null;
    
    try {
      const result = await modelRecommendService.recommendForDocument({
        document_id: documentId,
        document_name: documentName,
        chunks: chunks.map(c => ({
          chunk_id: c.chunk_id || c.id,
          content: c.content,
          chunk_type: c.chunk_type || 'text',
          metadata: c.metadata || {},
        })),
        top_n: topN,
      });
      
      recommendations.value = result.recommendations || [];
      documentAnalysis.value = result.document_analysis;
      topRecommendation.value = result.top_recommendation;
      
      // Auto-select top recommendation
      if (result.top_recommendation) {
        selectedModel.value = result.top_recommendation.model.model_name;
      }
      
      return result;
    } catch (err) {
      error.value = err.message || 'Failed to get recommendation';
      throw err;
    } finally {
      isLoading.value = false;
    }
  };
  
  /**
   * Get recommendation for batch documents.
   */
  const recommendForBatch = async (documents, topN = 3, outlierThreshold = null) => {
    isLoading.value = true;
    error.value = null;
    
    try {
      const result = await modelRecommendService.recommendForBatch({
        documents: documents.map(doc => ({
          document_id: doc.document_id || doc.id,
          document_name: doc.document_name || doc.name,
          chunks: (doc.chunks || []).map(c => ({
            chunk_id: c.chunk_id || c.id,
            content: c.content,
            chunk_type: c.chunk_type || 'text',
            metadata: c.metadata || {},
          })),
        })),
        top_n: topN,
        outlier_threshold: outlierThreshold,
      });
      
      batchResult.value = result;
      recommendations.value = result.unified_recommendation || [];
      
      // Auto-select top recommendation
      if (result.unified_recommendation?.length > 0) {
        selectedModel.value = result.unified_recommendation[0].model.model_name;
      }
      
      return result;
    } catch (err) {
      error.value = err.message || 'Failed to get batch recommendation';
      throw err;
    } finally {
      isLoading.value = false;
    }
  };
  
  /**
   * Analyze document features only.
   */
  const analyzeDocument = async (documentId, documentName, chunks) => {
    isAnalyzing.value = true;
    error.value = null;
    
    try {
      const result = await modelRecommendService.analyzeDocumentFeatures({
        document_id: documentId,
        document_name: documentName,
        chunks: chunks.map(c => ({
          chunk_id: c.chunk_id || c.id,
          content: c.content,
          chunk_type: c.chunk_type || 'text',
          metadata: c.metadata || {},
        })),
      });
      
      documentAnalysis.value = result;
      return result;
    } catch (err) {
      error.value = err.message || 'Failed to analyze document';
      throw err;
    } finally {
      isAnalyzing.value = false;
    }
  };
  
  /**
   * Load available models.
   */
  const loadModels = async (enabledOnly = true, modelType = null) => {
    isLoadingModels.value = true;
    
    try {
      const result = await modelRecommendService.listModels({
        enabled_only: enabledOnly,
        model_type: modelType,
      });
      
      availableModels.value = result.models || [];
      return result;
    } catch (err) {
      error.value = err.message || 'Failed to load models';
      throw err;
    } finally {
      isLoadingModels.value = false;
    }
  };
  
  /**
   * Load recommendation weights.
   */
  const loadWeights = async () => {
    try {
      const result = await modelRecommendService.getRecommendationWeights();
      recommendationWeights.value = result.weights;
      return result;
    } catch (err) {
      error.value = err.message || 'Failed to load weights';
      throw err;
    }
  };
  
  /**
   * Select a model for embedding.
   */
  const selectModel = (modelName) => {
    selectedModel.value = modelName;
  };
  
  /**
   * Clear all recommendation data.
   */
  const clearRecommendations = () => {
    recommendations.value = [];
    documentAnalysis.value = null;
    topRecommendation.value = null;
    batchResult.value = null;
    error.value = null;
  };
  
  /**
   * Reset store to initial state.
   */
  const reset = () => {
    clearRecommendations();
    selectedModel.value = '';
    availableModels.value = [];
    recommendationWeights.value = null;
  };
  
  return {
    // State
    recommendations,
    documentAnalysis,
    topRecommendation,
    batchResult,
    availableModels,
    recommendationWeights,
    isLoading,
    isAnalyzing,
    isLoadingModels,
    error,
    selectedModel,
    
    // Computed
    hasRecommendations,
    hasOutliers,
    outlierDocuments,
    textModels,
    multimodalModels,
    
    // Actions
    recommendForDocument,
    recommendForBatch,
    analyzeDocument,
    loadModels,
    loadWeights,
    selectModel,
    clearRecommendations,
    reset,
  };
});

export default useModelRecommendStore;
