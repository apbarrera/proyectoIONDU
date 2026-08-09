export type RecommendationPriority = 'alta' | 'media' | 'baja';

export interface Recommendation {
  id: string;
  title: string;
  description: string;
  category: string;
  relatedModule: string;
  dataUsed: string[];
  priority: RecommendationPriority;
}
