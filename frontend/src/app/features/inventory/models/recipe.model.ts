export interface RecipeIngredient {
  productId: string;
  quantity: number;
  unit: string;
}

export interface Recipe {
  id: string;
  productId: string;
  name: string;
  description: string;
  ingredients: RecipeIngredient[];
  yieldQuantity: number;
  notes?: string;
}
