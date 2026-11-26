export type RecommendationPriority = 'alta' | 'media' | 'baja';

/** Análisis del mes generado con IA (POST /api/recommendations/ai). Solo informativo. */
export interface AiAnalysis {
  analysis: string;
  recommendations: {
    title: string;
    description: string;
    category: string;
    priority: RecommendationPriority;
    dataUsed: string[];
  }[];
  generatedAt: string;
  model: string;
}

export interface Recommendation {
  id: string;
  title: string;
  description: string;
  category: string;
  relatedModule: string;
  dataUsed: string[];
  priority: RecommendationPriority;
}
